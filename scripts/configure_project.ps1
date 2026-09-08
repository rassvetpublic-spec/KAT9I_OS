param(
  [string]$Owner='rassvetpublic-spec',
  [string]$Repository='KAT9I_OS',
  [int]$ProjectNumber=2
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$ApiVersion='2026-03-10'

function Gql([string]$Query,[hashtable]$Variables){
  $payload=@{query=$Query;variables=$Variables}|ConvertTo-Json -Depth 30 -Compress
  $raw=$payload|gh api graphql --input -
  if($LASTEXITCODE -ne 0){throw 'GitHub GraphQL API вернул ошибку.'}
  $r=$raw|ConvertFrom-Json -Depth 30
  if($null -eq $r){throw 'GitHub GraphQL API вернул пустой ответ.'}
  $errorsProperty=$r.PSObject.Properties['errors']
  if($null -ne $errorsProperty -and $null -ne $errorsProperty.Value){
    $messages=@($errorsProperty.Value|ForEach-Object{
      $messageProperty=$_.PSObject.Properties['message']
      if($null -ne $messageProperty){$messageProperty.Value}else{$_|ConvertTo-Json -Depth 10 -Compress}
    })
    throw ($messages -join '; ')
  }
  $r
}
function Rest([string]$Endpoint,[string]$Method='GET',$Body=$null){
  $a=@('api','--method',$Method,'-H','Accept: application/vnd.github+json','-H',"X-GitHub-Api-Version: $ApiVersion")
  if($null -ne $Body){$raw=($Body|ConvertTo-Json -Depth 30 -Compress)|gh @a --input - $Endpoint}else{$raw=gh @a $Endpoint}
  if($LASTEXITCODE -ne 0){throw "GitHub REST API вернул ошибку: $Endpoint"}
  if([string]::IsNullOrWhiteSpace($raw)){return $null}
  $raw|ConvertFrom-Json -Depth 30
}
function Snapshot{
$q=@'
query($login:String!,$number:Int!,$repo:String!){
 user(login:$login){id projectV2(number:$number){id title url repositories(first:100){nodes{id nameWithOwner}} fields(first:100){nodes{__typename ... on ProjectV2Field{id name dataType} ... on ProjectV2SingleSelectField{id name dataType options{id name color description}} ... on ProjectV2IterationField{id name dataType configuration{duration startDay}}}} views(first:100){nodes{id name layout filter}}}}
 repository(owner:$login,name:$repo){id nameWithOwner}
}
'@
 (Gql $q @{login=$Owner;number=$ProjectNumber;repo=$Repository}).data
}
function Opt([string]$Name,[string]$Color,[string]$Description,[string[]]$Aliases=@()){
  if($Aliases.Count -eq 0){$Aliases=@($Name)}
  [ordered]@{name=$Name;color=$Color;description=$Description;aliases=$Aliases}
}
function EnsureSelect([string]$Name,[string[]]$FieldAliases,[object[]]$Defs){
  if($FieldAliases.Count -eq 0){$FieldAliases=@($Name)}
  $p=(Snapshot).user.projectV2
  $f=@($p.fields.nodes)|Where-Object{$FieldAliases -contains $_.name}|Select-Object -First 1
  if(-not $f){
$q=@'
mutation($input:CreateProjectV2FieldInput!){createProjectV2Field(input:$input){projectV2Field{... on ProjectV2SingleSelectField{id name options{id name}}}}}
'@
    $opts=@($Defs|ForEach-Object{[ordered]@{name=$_.name;color=$_.color;description=$_.description}})
    $null=Gql $q @{input=@{projectId=$p.id;name=$Name;dataType='SINGLE_SELECT';singleSelectOptions=$opts}}
    Write-Host "Создано поле: $Name";return
  }
  if($f.__typename -ne 'ProjectV2SingleSelectField'){throw "Поле '$($f.name)' уже существует с другим типом."}
  $known=@($Defs|ForEach-Object{$_.aliases})
  $unknown=@($f.options|Where-Object{$known -notcontains $_.name})
  if($unknown.Count -gt 0){throw "Поле '$($f.name)' содержит неизвестные значения: $(($unknown.name)-join ', '). Автоматическое удаление запрещено."}
  $opts=@()
  foreach($d in $Defs){
    $old=@($f.options)|Where-Object{$d.aliases -contains $_.name}|Select-Object -First 1
    $o=[ordered]@{name=$d.name;color=$d.color;description=$d.description};if($old){$o.id=$old.id};$opts+=$o
  }
$q=@'
mutation($input:UpdateProjectV2FieldInput!){updateProjectV2Field(input:$input){projectV2Field{... on ProjectV2SingleSelectField{id name options{id name}}}}}
'@
  $null=Gql $q @{input=@{fieldId=$f.id;name=$Name;singleSelectOptions=$opts}}
  if($f.name -ne $Name){Write-Host "Переименовано поле: $($f.name) -> $Name"}else{Write-Host "Проверено поле: $Name"}
}
function Monday{
  $d=(Get-Date).Date;$n=([int]$d.DayOfWeek+6)%7;$d.AddDays(-$n).ToString('yyyy-MM-dd')
}
function EnsureIteration{
  $p=(Snapshot).user.projectV2
  $f=@($p.fields.nodes)|Where-Object{$_.name -eq 'Итерация'}|Select-Object -First 1
  if($f){
    if($f.__typename -ne 'ProjectV2IterationField'){throw 'Поле Итерация существует с другим типом.'}
    if($f.configuration.duration -eq 3){Write-Host 'Проверено поле: Итерация (3 дня)';return}
    if($f.configuration.duration -ne 7){throw "Неожиданная длительность Итерации: $($f.configuration.duration) дней. Автоматическое изменение запрещено."}
$q=@'
mutation($input:UpdateProjectV2FieldInput!){updateProjectV2Field(input:$input){projectV2Field{... on ProjectV2IterationField{id name configuration{duration}}}}}
'@
    $null=Gql $q @{input=@{fieldId=$f.id;iterationConfiguration=@{startDate=(Monday);duration=3;iterations=@()}}}
    Write-Host 'Итерация изменена: 7 -> 3 дня'
    return
  }
$q=@'
mutation($input:CreateProjectV2FieldInput!){createProjectV2Field(input:$input){projectV2Field{... on ProjectV2IterationField{id name}}}}
'@
  $null=Gql $q @{input=@{projectId=$p.id;name='Итерация';dataType='ITERATION';iterationConfiguration=@{startDate=(Monday);duration=3;iterations=@()}}}
  Write-Host 'Создано поле Итерация: 3 дня'
}
function EnsureLink{
  $s=Snapshot;$p=$s.user.projectV2;$repo=$s.repository
  if($p.title -ne 'KAT9I_OS — разработка'){
$q=@'
mutation($input:UpdateProjectV2Input!){updateProjectV2(input:$input){projectV2{id title}}}
'@
    $null=Gql $q @{input=@{projectId=$p.id;title='KAT9I_OS — разработка'}}
  }
  if(-not (@($p.repositories.nodes)|Where-Object{$_.id -eq $repo.id})){
$q=@'
mutation($input:LinkProjectV2ToRepositoryInput!){linkProjectV2ToRepository(input:$input){repository{id}}}
'@
    $null=Gql $q @{input=@{projectId=$p.id;repositoryId=$repo.id}}
  }
}
function EnsureItems{
  $repo="$Owner/$Repository";$urls=@()
  $j=gh issue list --repo $repo --state open --limit 1000 --json url;if($LASTEXITCODE -eq 0 -and $j){$urls+=@(($j|ConvertFrom-Json).url)}
  $j=gh pr list --repo $repo --state open --limit 1000 --json url;if($LASTEXITCODE -eq 0 -and $j){$urls+=@(($j|ConvertFrom-Json).url)}
  $urls+="https://github.com/$repo/issues/62"
  foreach($u in @($urls|Sort-Object -Unique)){$null=gh project item-add $ProjectNumber --owner $Owner --url $u --format json 2>&1;if($LASTEXITCODE -ne 0){throw "Не удалось добавить $u"}}
  Write-Host 'Актуальные открытые Issues/PR и управляющая Issue #62 добавлены.'
}
function EnsureViews{
  $p=(Snapshot).user.projectV2
  $required=@('Статус','Этап','Приоритет','Область','Исполнитель','Проверяющий','Исполнение')
  $m=@{}
  for($attempt=1;$attempt -le 10;$attempt++){
    $rf=Rest "users/$Owner/projectsV2/$ProjectNumber/fields?per_page=100"
    $m=@{}
    foreach($f in @($rf)){$m[$f.name]=$f}
    $missing=@($required|Where-Object{-not $m.ContainsKey($_)})
    if($missing.Count -eq 0){break}
    if($attempt -lt 10){Write-Host "GitHub ещё синхронизирует поля. Повтор $attempt/10...";Start-Sleep -Seconds 2}
  }
  $missing=@($required|Where-Object{-not $m.ContainsKey($_)})
  if($missing.Count -gt 0){throw "После ожидания API не видит поля: $(($missing)-join ', '). Повторите запуск через несколько секунд."}
  $vid=@();foreach($n in @('Title','Assignees','Статус','Этап','Приоритет','Область','Тип','Размер','Итерация','Исполнитель','Проверяющий','Исполнение','Цель','Риск','Доказательство','Linked pull requests','Sub-issues progress')){if($m.ContainsKey($n)){$vid+=[int64]$m[$n].id}}
  $id=@{};foreach($n in $required){$id[$n]=[int64]$m[$n].id}
  $u=Rest "users/$Owner";$uid=[string]$u.id
  $views=@(
    @{n='00 — Центр управления';l='table';f='is:open';s=@(@($id['Этап'],'asc'),@($id['Приоритет'],'asc'),@($id['Статус'],'asc'))},
    @{n='01 — Архитектура G1';l='table';f='is:open Этап:"G1 — ТЗ и базовая архитектура"';s=@(@($id['Приоритет'],'asc'),@($id['Статус'],'asc'))},
    @{n='02 — Готово к работе';l='table';f='is:open Статус:"Готово к работе" -Исполнение:"Заблокировано"';s=@(@($id['Приоритет'],'asc'))},
    @{n='03 — Активные исполнители';l='board';f='is:open Исполнение:"Активно"';s=@(@($id['Приоритет'],'asc'));v=@($id['Исполнитель'])},
    @{n='04 — Очередь проверки';l='board';f='is:open Статус:"Проверка качества"';s=@(@($id['Приоритет'],'asc'));v=@($id['Проверяющий'])},
    @{n='05 — Заблокировано';l='table';f='is:open Статус:"Заблокировано"';s=@(@($id['Этап'],'asc'),@($id['Приоритет'],'asc'))},
    @{n='06 — План v0.1';l='roadmap';f='is:open Цель:v0.1'},
    @{n='07 — Безопасность';l='table';f='is:open Область:"Безопасность и управление"';s=@(@($id['Приоритет'],'asc'),@($id['Статус'],'asc'))},
    @{n='08 — Доказательства';l='table';f='is:open Приоритет:P0,P1 -Доказательство:"Проверка качества пройдена"';s=@(@($id['Приоритет'],'asc'),@($id['Этап'],'asc'))},
    @{n='09 — Без классификации';l='table';f='is:open no:Этап no:Приоритет'}
  )
  foreach($v in $views){
    if(@($p.views.nodes)|Where-Object{$_.name -eq $v['n']}){continue}
    $b=[ordered]@{name=$v['n'];layout=$v['l'];filter=$v['f']}
    if($v['l'] -ne 'roadmap'){$b.visible_fields=$vid}
    if($v.ContainsKey('s')){$b.sort_by=$v['s']}
    if($v.ContainsKey('v')){$b.vertical_group_by=$v['v']}
    try{$null=Rest "users/$uid/projectsV2/$ProjectNumber/views" 'POST' $b;Write-Host "Создано представление: $($v['n'])"}catch{Write-Warning "Не удалось создать '$($v['n'])' через API: $($_.Exception.Message)"}
  }
  $p=(Snapshot).user.projectV2
  $hasCanonical=@($p.views.nodes)|Where-Object{$_.name -eq '00 — Центр управления'}|Select-Object -First 1
  $blank=@($p.views.nodes)|Where-Object{$_.name -eq 'View 1' -and $_.layout -eq 'TABLE' -and [string]::IsNullOrWhiteSpace($_.filter)}|Select-Object -First 1
  if($hasCanonical -and $blank){
$q=@'
mutation($input:DeleteProjectV2ViewInput!){deleteProjectV2View(input:$input){projectV2View{id}}}
'@
    $null=Gql $q @{input=@{viewId=$blank.id}}
    Write-Host 'Удалено пустое представление View 1.'
  }
  if($hasCanonical){
    $oldNames=@(
      '00 — Control Tower','01 — Architecture G1','02 — Ready Queue','03 — Active Workers',
      '04 — QA Queue','05 — Blocked','06 — v0.1 Roadmap','07 — Security',
      '08 — Evidence / Compliance','09 — Unclassified'
    )
    foreach($old in @($p.views.nodes|Where-Object{$oldNames -contains $_.name})){
$q=@'
mutation($input:DeleteProjectV2ViewInput!){deleteProjectV2View(input:$input){projectV2View{id}}}
'@
      $null=Gql $q @{input=@{viewId=$old.id}}
      Write-Host "Удалено старое англоязычное представление: $($old.name)"
    }
  }
}

if(-not(Get-Command gh -ErrorAction SilentlyContinue)){throw 'GitHub CLI (gh) не найден.'}
$null=gh auth status 2>&1;if($LASTEXITCODE -ne 0){throw 'GitHub CLI не авторизован.'}
$null=gh project view $ProjectNumber --owner $Owner --format json 2>&1;if($LASTEXITCODE -ne 0){throw 'Нужен scope project. Авторизуйте GitHub CLI с разрешением project.'}

EnsureLink
EnsureSelect 'Статус' @('Статус','Status') @(
 (Opt 'Входящие' 'GRAY' 'Новая работа.' @('Входящие','Todo')),
 (Opt 'Нужно разобрать' 'YELLOW' 'Нужно определить этап, приоритет, границы работы и зависимости.' @('Нужно разобрать','Разбор')),
 (Opt 'Готово к работе' 'BLUE' 'Задачу можно брать.'),
 (Opt 'В работе' 'ORANGE' 'Идёт активная работа.' @('В работе','In Progress')),
 (Opt 'Проверка качества' 'PURPLE' 'Результат проходит проверку качества.' @('Проверка качества','Проверка QA','QA')),
 (Opt 'Заблокировано' 'RED' 'Есть причина, мешающая продолжить работу.' @('Заблокировано','Blocked')),
 (Opt 'Готово' 'GREEN' 'Работа завершена по правилам.' @('Готово','Done'))
)
EnsureSelect 'Этап' @('Этап','Gate') @(
 (Opt 'G0 — Порядок проекта и задач' 'GRAY' 'Порядок GitHub Project и списка задач.' @('G0 — Порядок проекта и задач','G0 — Project/Backlog Hygiene','G0')),
 (Opt 'G1 — ТЗ и базовая архитектура' 'BLUE' 'ТЗ и принятая базовая архитектура.' @('G1 — ТЗ и базовая архитектура','G1 — ТЗ и Architecture Baseline','G1')),
 (Opt 'G2 — Машинные контракты' 'PURPLE' 'Форматы и правила обмена данными между частями системы.' @('G2 — Машинные контракты','G2 — Machine Contracts','G2')),
 (Opt 'G3 — Основа исполняемой системы' 'ORANGE' 'Фундамент исполняемой системы.' @('G3 — Основа исполняемой системы','G3 — Runtime Foundation','G3')),
 (Opt 'G4 — Сквозная версия v0.1' 'GREEN' 'Первая сквозная рабочая версия.' @('G4 — Сквозная версия v0.1','G4 — Vertical v0.1','G4')),
 (Opt 'G5 — После v0.1' 'YELLOW' 'Работы после первой версии.' @('G5 — После v0.1','G5 — после v0.1','G5'))
)
EnsureSelect 'Приоритет' @('Приоритет','Priority') @(
 (Opt 'P0' 'RED' 'Критично.' @('P0','Urgent')),
 (Opt 'P1' 'ORANGE' 'Важно.' @('P1','High')),
 (Opt 'P2' 'YELLOW' 'Полезно.' @('P2','Medium')),
 (Opt 'P3' 'GRAY' 'Можно позже.' @('P3','Low'))
)
EnsureSelect 'Тип' @('Тип','Тип работы','Work Type') @(
 (Opt 'ТЗ / архитектура' 'BLUE' 'Требования и архитектура.' @('ТЗ / архитектура','ТЗ/Architecture')),
 (Opt 'Документация' 'GRAY' 'Документация.' @('Документация','Documentation')),
 (Opt 'Исследование' 'PURPLE' 'Исследование.' @('Исследование','Research')),
 (Opt 'Инфраструктура' 'ORANGE' 'Инструменты, GitHub и автоматизация.' @('Инфраструктура','Infrastructure')),
 (Opt 'Контракты' 'BLUE' 'Машинные контракты.' @('Контракты','Contract')),
 (Opt 'Исполняемая система' 'GREEN' 'Рабочая логика системы.' @('Исполняемая система','Runtime')),
 (Opt 'Безопасность' 'RED' 'Безопасность.' @('Безопасность','Security')),
 (Opt 'Проверка качества / оценка' 'YELLOW' 'Проверка качества и измерение результата.' @('Проверка качества / оценка','QA/Eval'))
)
EnsureSelect 'Область' @('Область') @(
 (Opt 'Архитектура и документация' 'BLUE' 'Архитектура и единый источник истины.'),
 (Opt 'Контекст и знания' 'PURPLE' 'Контекст, память и знания.' @('Контекст и знания')),
 (Opt 'Исполнение и исполнители' 'GREEN' 'Исполнение задач и исполнители.' @('Исполнение и исполнители','Исполнение и Workers')),
 (Opt 'Безопасность и управление' 'RED' 'Безопасность и правила управления.'),
 (Opt 'Интерфейс и визуализация' 'YELLOW' 'Интерфейс и отображение информации.'),
 (Opt 'Инженерная инфраструктура' 'ORANGE' 'GitHub, CI и инструменты.'),
 (Opt 'Общее / не определено' 'GRAY' 'Ещё не классифицировано.')
)
EnsureSelect 'Размер' @('Размер') @(
 (Opt 'XS — совсем маленькая' 'GRAY' 'Совсем маленькая.' @('XS — совсем маленькая','XS')),
 (Opt 'S — маленькая' 'BLUE' 'Маленькая.' @('S — маленькая','S')),
 (Opt 'M — средняя' 'YELLOW' 'Средняя.' @('M — средняя','M')),
 (Opt 'L — большая' 'ORANGE' 'Большая.' @('L — большая','L')),
 (Opt 'XL — очень большая' 'RED' 'Нужно разбить на более мелкие задачи.' @('XL — очень большая','XL'))
)
$workers=@(
 (Opt 'ChatGPT' 'GREEN' 'ChatGPT.'),
 (Opt 'AGY' 'BLUE' 'AGY.'),
 (Opt 'Codex' 'PURPLE' 'Codex.'),
 (Opt 'Человек' 'ORANGE' 'Человек.' @('Человек','Human')),
 (Opt 'Другой' 'GRAY' 'Другой исполнитель.' @('Другой','Other'))
)
EnsureSelect 'Исполнитель' @('Исполнитель','Implementation Worker') $workers
EnsureSelect 'Проверяющий' @('Проверяющий','QA Worker') $workers
EnsureSelect 'Исполнение' @('Исполнение','Состояние работы','Claim') @(
 (Opt 'Свободно' 'GRAY' 'Никто не взял работу.' @('Свободно','UNCLAIMED')),
 (Opt 'В очереди' 'BLUE' 'Работа зарезервирована.' @('В очереди','QUEUED')),
 (Opt 'Активно' 'ORANGE' 'Исполнитель прямо сейчас работает над задачей.' @('Активно','В работе','ACTIVE')),
 (Opt 'На проверке' 'PURPLE' 'Работа передана отдельному проверяющему.' @('На проверке','QA')),
 (Opt 'Заблокировано' 'RED' 'Продолжение работы заблокировано.' @('Заблокировано','BLOCKED')),
 (Opt 'Освобождено' 'GREEN' 'Исполнитель освободил задачу после завершения работы.' @('Освобождено','Завершено','RELEASED'))
)
EnsureSelect 'Цель' @('Цель','Target') @(
 (Opt 'Базовая архитектура' 'BLUE' 'Базовая принятая архитектура.' @('Базовая архитектура','Architecture Baseline')),
 (Opt 'v0.1' 'GREEN' 'Первая рабочая версия.'),
 (Opt 'v0.2' 'PURPLE' 'Следующая версия.'),
 (Opt 'v1.0' 'ORANGE' 'Первая стабильная версия.'),
 (Opt 'Позже' 'GRAY' 'Не входит в ближайшие версии.' @('Позже','Later'))
)
EnsureSelect 'Риск' @('Риск','Risk') @(
 (Opt 'Критический' 'RED' 'Критический риск.' @('Критический','Critical')),
 (Opt 'Высокий' 'ORANGE' 'Высокий риск.' @('Высокий','High')),
 (Opt 'Средний' 'YELLOW' 'Средний риск.' @('Средний','Medium')),
 (Opt 'Низкий' 'GREEN' 'Низкий риск.' @('Низкий','Low'))
)
EnsureSelect 'Доказательство' @('Доказательство','Evidence') @(
 (Opt 'Нет' 'RED' 'Подтверждения результата пока нет.' @('Нет','Missing')),
 (Opt 'Частично' 'YELLOW' 'Есть только часть подтверждений.' @('Частично','Partial')),
 (Opt 'Автопроверки пройдены' 'BLUE' 'Автоматические проверки пройдены на точной версии.' @('Автопроверки пройдены','CI PASS')),
 (Opt 'Проверка качества пройдена' 'GREEN' 'Независимая проверка качества пройдена на точной версии.' @('Проверка качества пройдена','QA PASS'))
)
EnsureIteration
EnsureItems
EnsureViews
Write-Host 'Проект #2 настроен. Слияние, прохождение проверки качества и прохождение этапа этот настройщик никогда не выполняет автоматически.'
