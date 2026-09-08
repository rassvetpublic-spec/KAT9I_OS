param(
    [string]$Owner = 'rassvetpublic-spec',
    [int]$ProjectNumber = 2
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-GraphQL {
    param(
        [Parameter(Mandatory = $true)][string]$Query,
        [Parameter(Mandatory = $true)][hashtable]$Variables
    )

    $payload = @{
        query = $Query
        variables = $Variables
    } | ConvertTo-Json -Depth 30 -Compress

    $resultText = $payload | gh api graphql --input -
    if ($LASTEXITCODE -ne 0) {
        throw 'GitHub GraphQL API вернул ошибку.'
    }

    return ($resultText | ConvertFrom-Json -Depth 30)
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw 'GitHub CLI (gh) не найден. Установите GitHub CLI и повторите запуск.'
}

$null = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    throw 'GitHub CLI не авторизован. Сначала выполните вход через gh auth login.'
}

$null = gh project view $ProjectNumber --owner $Owner --format json 2>&1
if ($LASTEXITCODE -ne 0) {
    throw 'Нет доступа к GitHub Project. Для записи нужен scope project. Выполните gh auth refresh -s project и повторите запуск.'
}

$query = @'
query($login: String!, $number: Int!) {
  user(login: $login) {
    projectV2(number: $number) {
      id
      title
      fields(first: 100) {
        nodes {
          __typename
          ... on ProjectV2Field {
            id
            name
            dataType
          }
          ... on ProjectV2SingleSelectField {
            id
            name
            options {
              id
              name
              color
              description
            }
          }
        }
      }
    }
  }
}
'@

$response = Invoke-GraphQL -Query $query -Variables @{ login = $Owner; number = $ProjectNumber }
$project = $response.data.user.projectV2
if (-not $project) {
    throw "Project #$ProjectNumber у пользователя $Owner не найден."
}

$status = @($project.fields.nodes) | Where-Object {
    $_.__typename -eq 'ProjectV2SingleSelectField' -and $_.name -eq 'Status'
} | Select-Object -First 1

if (-not $status) {
    throw 'Системное поле Status не найдено.'
}

$definitions = @(
    @{ name = 'Входящие'; aliases = @('Входящие', 'Todo'); color = 'GRAY'; description = 'Новая работа, которая только попала в проект.' },
    @{ name = 'Нужно разобрать'; aliases = @('Нужно разобрать', 'Разбор'); color = 'YELLOW'; description = 'Нужно определить Gate, приоритет, Scope и зависимости.' },
    @{ name = 'Готово к работе'; aliases = @('Готово к работе'); color = 'BLUE'; description = 'Задача понятна и может быть взята исполнителем.' },
    @{ name = 'В работе'; aliases = @('В работе', 'In Progress'); color = 'ORANGE'; description = 'По задаче идёт активная работа.' },
    @{ name = 'Проверка QA'; aliases = @('Проверка QA', 'QA'); color = 'PURPLE'; description = 'Результат проходит review и независимую проверку качества.' },
    @{ name = 'Заблокировано'; aliases = @('Заблокировано', 'Blocked'); color = 'RED'; description = 'Продолжать нельзя до устранения блокера.' },
    @{ name = 'Готово'; aliases = @('Готово', 'Done'); color = 'GREEN'; description = 'Работа завершена по правилам проекта.' }
)

$knownAliases = @($definitions | ForEach-Object { $_.aliases })
$unknown = @($status.options | Where-Object { $knownAliases -notcontains $_.name })
if ($unknown.Count -gt 0) {
    $names = ($unknown | ForEach-Object { $_.name }) -join ', '
    throw "В Status найдены неизвестные значения: $names. Скрипт остановлен без изменений, чтобы не потерять данные."
}

$options = @()
foreach ($definition in $definitions) {
    $existing = @($status.options) | Where-Object { $definition.aliases -contains $_.name } | Select-Object -First 1
    $item = [ordered]@{
        name = $definition.name
        color = $definition.color
        description = $definition.description
    }
    if ($existing) {
        $item.id = $existing.id
    }
    $options += $item
}

$mutation = @'
mutation($input: UpdateProjectV2FieldInput!) {
  updateProjectV2Field(input: $input) {
    projectV2Field {
      ... on ProjectV2SingleSelectField {
        id
        name
        options {
          id
          name
        }
      }
    }
  }
}
'@

$variables = @{
    input = @{
        fieldId = $status.id
        singleSelectOptions = $options
    }
}

$updated = Invoke-GraphQL -Query $mutation -Variables $variables
$result = $updated.data.updateProjectV2Field.projectV2Field

Write-Host "Project: $($project.title) (#$ProjectNumber)"
Write-Host 'Status настроен:'
$result.options | ForEach-Object { Write-Host "- $($_.name)" }
Write-Host 'Готово. Существующие Todo/In Progress/Done переименованы с сохранением их ID и значений карточек.'
