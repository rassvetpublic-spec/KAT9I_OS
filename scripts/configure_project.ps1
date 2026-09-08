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
  if($r.errors){throw (($r.errors|ForEach-Object{$_.message})-join '; ')}
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
function EnsureSelect([string]$Name,[object[]]$Defs){
  $p=(Snapshot).user.projectV2
  $f=@($p.fields.nodes)|Where-Object{$_.name -eq $Name}|Select-Object -First 1
  if(-not $f){
$q=@'
mutation($input:CreateProjectV2FieldInput!){createProjectV2Field(input:$input){projectV2Field{... on ProjectV2SingleSelectField{id name options{id name}}}}}
'@
    $opts=@($Defs|ForEach-Object{[ordered]@{name=$_.name;color=$_.color;description=$_.description}})
    $null=Gql $q @{input=@{projectId=$p.id;name=$Name;dataType='SINGLE_SELECT';singleSelectOptions=$opts}}
    Write-Host "Создано поле: $Name";return
  }
  if($f.__typename -ne 'ProjectV2SingleSelectField'){throw "Поле '$Name' уже существует с другим типом."}
  $known=@($Defs|ForEach-Object{$_.aliases})
  $unknown=@($f.options|Where-Object{$known -notcontains $_.name})
  if($unknown.Count -gt 0){throw "Поле '$Name' содержит неизвестные значения: $(($unknown.name)-join ', '). Автоматическое удаление запрещено."}
  $opts=@()
  foreach($d in $Defs){
    $old=@($f.options)|Where-Object{$d.aliases -contains $_.name}|Select-Object -First 1
    $o=[ordered]@{name=$d.name;color=$d.color;description=$d.description};if($old){$o.id=$old.id};$opts+=$o
  }
$q=@'
mutation($input:UpdateProjectV2FieldInput!){updateProjectV2Field(input:$input){projectV2Field{... on ProjectV2SingleSelectField{id name options{id name}}}}}
'@
  $null=Gql $q @{input=@{fieldId=$f.id;singleSelectOptions=$opts}}
  Write-Host "Проверено поле: $Name"
}
function Monday{
  $d=(Get-Date).Date;$n=([int]$d.DayOfWeek+6)%7;$d.AddDays(-$n).ToString('yyyy-MM-dd')
}
function EnsureIteration{
  $p=(Snapshot).user.projectV2
  $f=@($p.fields.nodes)|Where-Object{$_.name -eq 'Итерация'}|Select-Object -First 1
  if($f){if($f.__typename -ne 'ProjectV2IterationField'){throw 'Поле Итерация существует с другим типом.'};if($f.configuration.duration -ne 7){throw 'Существующая Итерация не недельная; автоматическое изменение запрещено.'};Write-Host 'Проверено поле: Итерация';return}
$q=@'
mutation($input:CreateProjectV2FieldInput!){createProjectV2Field(input:$input){projectV2Field{... on ProjectV2IterationField{id name}}}}
'@
  $null=Gql $q @{input=@{projectId=$p.id;name='Итерация';dataType='ITERATION';iterationConfiguration=@{startDate=(Monday);duration=7;iterations=@()}}}
  Write-Host 'Создано недельное поле: Итерация'
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
  $blank=@($p.views.nodes)|Where-Object{$_.name -eq 'View 1' -and $_.layout -eq 'TABLE' -and [string]::IsNullOrWhiteSpace($_.filter)}|Select-Object -First 1
  if($blank){
$q=@'
mutation($input:DeleteProjectV2ViewInput!){deleteProjectV2View(input:$input){projectV2View{id}}}
'@
    $null=Gql $q @{input=@{viewId=$blank.id}}
    $p=(Snapshot).user.projectV2
  }
  $rf=Rest "users/$Owner/projectsV2/$ProjectNumber/fields?per_page=100";$m=@{};foreach($f in @($rf)){$m[$f.name]=$f}
  $vid=@();foreach($n in @('Title','Assignees','Status','Gate','Priority','Область','Work Type','Размер','Итерация','Implementation Worker','QA Worker','Claim','Target','Risk','Evidence','Linked pull requests','Sub-issues progress')){if($m.ContainsKey($n)){$vid+=[int64]$m[$n].id}}
  $id=@{};foreach($n in @('Status','Gate','Priority','Область','Implementation Worker','QA Worker','Claim')){if(-not $m.ContainsKey($n)){throw "Для представлений не найдено поле $n"};$id[$n]=[int64]$m[$n].id}
  $u=Rest "users/$Owner";$uid=[string]$u.id
  $views=@(
    @{n='00 — Control Tower';l='table';f='is:open';s=@(@($id['Gate'],'asc'),@($id['Priority'],'asc'),@($id['Status'],'asc'))},
    @{n='01 — Architecture G1';l='table';f='is:open Gate:"G1 — ТЗ и Architecture Baseline"';s=@(@($id['Priority'],'asc'),@($id['Status'],'asc'))},
    @{n='02 — Ready Queue';l='table';f='is:open Status:"Готово к работе" -Claim:BLOCKED';s=@(@($id['Priority'],'asc'))},
    @{n='03 — Active Workers';l='board';f='is:open Claim:ACTIVE';s=@(@($id['Priority'],'asc'));v=@($id['Implementation Worker'])},
    @{n='04 — QA Queue';l='board';f='is:open Status:"Проверка QA"';s=@(@($id['Priority'],'asc'));v=@($id['QA Worker'])},
    @{n='05 — Blocked';l='table';f='is:open Status:"Заблокировано"';s=@(@($id['Gate'],'asc'),@($id['Priority'],'asc'))},
    @{n='06 — v0.1 Roadmap';l='roadmap';f='is:open Target:v0.1'},
    @{n='07 — Security';l='table';f='is:open Область:"Безопасность и управление"';s=@(@($id['Priority'],'asc'),@($id['Status'],'asc'))},
    @{n='08 — Evidence / Compliance';l='table';f='is:open Priority:P0,P1 -Evidence:"QA PASS"';s=@(@($id['Priority'],'asc'),@($id['Gate'],'asc'))},
    @{n='09 — Unclassified';l='table';f='is:open no:Gate no:Priority'}
  )
  foreach($v in $views){
    if(@($p.views.nodes)|Where-Object{$_.name -eq $v['n']}){continue}
    $b=[ordered]@{name=$v['n'];layout=$v['l'];filter=$v['f']}
    if($v['l'] -ne 'roadmap'){$b.visible_fields=$vid}
    if($v.ContainsKey('s')){$b.sort_by=$v['s']}
    if($v.ContainsKey('v')){$b.vertical_group_by=$v['v']}
    try{$null=Rest "users/$uid/projectsV2/$ProjectNumber/views" 'POST' $b;Write-Host "Создано представление: $($v['n'])"}catch{Write-Warning "Не удалось создать '$($v['n'])' через REST API: $($_.Exception.Message)"}
  }
}

if(-not(Get-Command gh -ErrorAction SilentlyContinue)){throw 'GitHub CLI (gh) не найден.'}
$null=gh auth status 2>&1;if($LASTEXITCODE -ne 0){throw 'GitHub CLI не авторизован.'}
$null=gh project view $ProjectNumber --owner $Owner --format json 2>&1;if($LASTEXITCODE -ne 0){throw 'Нужен scope project. Авторизуйте GitHub CLI с разрешением project.'}

EnsureLink
EnsureSelect 'Status' @(
 (Opt 'Входящие' 'GRAY' 'Новая работа.' @('Входящие','Todo')),
 (Opt 'Нужно разобрать' 'YELLOW' 'Нужно определить Gate, приоритет, Scope и зависимости.' @('Нужно разобрать','Разбор')),
 (Opt 'Готово к работе' 'BLUE' 'Задачу можно брать.'),
 (Opt 'В работе' 'ORANGE' 'Идёт активная работа.' @('В работе','In Progress')),
 (Opt 'Проверка QA' 'PURPLE' 'Review и независимый QA.' @('Проверка QA','QA')),
 (Opt 'Заблокировано' 'RED' 'Есть блокер.' @('Заблокировано','Blocked')),
 (Opt 'Готово' 'GREEN' 'Работа завершена по правилам.' @('Готово','Done'))
)
EnsureSelect 'Gate' @(
 (Opt 'G0 — Project/Backlog Hygiene' 'GRAY' 'GitHub Control Plane и backlog.' @('G0 — Project/Backlog Hygiene','G0')),
 (Opt 'G1 — ТЗ и Architecture Baseline' 'BLUE' 'ТЗ и Architecture Baseline.' @('G1 — ТЗ и Architecture Baseline','G1')),
 (Opt 'G2 — Machine Contracts' 'PURPLE' 'Машинные контракты.' @('G2 — Machine Contracts','G2')),
 (Opt 'G3 — Runtime Foundation' 'ORANGE' 'Фундамент Runtime.' @('G3 — Runtime Foundation','G3')),
 (Opt 'G4 — Vertical v0.1' 'GREEN' 'Первая сквозная версия.' @('G4 — Vertical v0.1','G4')),
 (Opt 'G5 — после v0.1' 'YELLOW' 'После v0.1.' @('G5 — после v0.1','G5'))
)
EnsureSelect 'Priority' @(
 (Opt 'P0' 'RED' 'Критично.' @('P0','Urgent')),(Opt 'P1' 'ORANGE' 'Важно.' @('P1','High')),(Opt 'P2' 'YELLOW' 'Полезно.' @('P2','Medium')),(Opt 'P3' 'GRAY' 'Позже.' @('P3','Low'))
)
EnsureSelect 'Work Type' @((Opt 'ТЗ/Architecture' 'BLUE' 'ТЗ и архитектура.'),(Opt 'Documentation' 'GRAY' 'Документация.'),(Opt 'Research' 'PURPLE' 'Исследование.'),(Opt 'Infrastructure' 'ORANGE' 'Инфраструктура.'),(Opt 'Contract' 'BLUE' 'Контракты.'),(Opt 'Runtime' 'GREEN' 'Runtime.'),(Opt 'Security' 'RED' 'Безопасность.'),(Opt 'QA/Eval' 'YELLOW' 'QA и evals.'))
EnsureSelect 'Область' @((Opt 'Архитектура и документация' 'BLUE' 'SSoT и архитектура.'),(Opt 'Контекст и знания' 'PURPLE' 'Context и Knowledge.'),(Opt 'Исполнение и Workers' 'GREEN' 'Workers и execution.'),(Opt 'Безопасность и управление' 'RED' 'Security и governance.'),(Opt 'Интерфейс и визуализация' 'YELLOW' 'UI и UX.'),(Opt 'Инженерная инфраструктура' 'ORANGE' 'CI, GitHub и инструменты.'),(Opt 'Общее / не определено' 'GRAY' 'Ещё не классифицировано.'))
EnsureSelect 'Размер' @((Opt 'XS — совсем маленькая' 'GRAY' 'Минимальная.' @('XS — совсем маленькая','XS')),(Opt 'S — маленькая' 'BLUE' 'Маленькая.' @('S — маленькая','S')),(Opt 'M — средняя' 'YELLOW' 'Средняя.' @('M — средняя','M')),(Opt 'L — большая' 'ORANGE' 'Большая.' @('L — большая','L')),(Opt 'XL — очень большая' 'RED' 'Нужна декомпозиция.' @('XL — очень большая','XL')))
$workers=@((Opt 'ChatGPT' 'GREEN' 'ChatGPT.'),(Opt 'AGY' 'BLUE' 'AGY.'),(Opt 'Codex' 'PURPLE' 'Codex.'),(Opt 'Human' 'ORANGE' 'Человек.'),(Opt 'Другой' 'GRAY' 'Другой Worker.' @('Другой','Other')))
EnsureSelect 'Implementation Worker' $workers
EnsureSelect 'QA Worker' $workers
EnsureSelect 'Claim' @((Opt 'UNCLAIMED' 'GRAY' 'Не заявлено.'),(Opt 'QUEUED' 'BLUE' 'Зарезервировано.'),(Opt 'ACTIVE' 'ORANGE' 'Активная работа.'),(Opt 'QA' 'PURPLE' 'На QA.'),(Opt 'BLOCKED' 'RED' 'Заблокировано.'),(Opt 'RELEASED' 'GREEN' 'Освобождено.'))
EnsureSelect 'Target' @((Opt 'Architecture Baseline' 'BLUE' 'Architecture Baseline.'),(Opt 'v0.1' 'GREEN' 'v0.1.'),(Opt 'v0.2' 'PURPLE' 'v0.2.'),(Opt 'v1.0' 'ORANGE' 'v1.0.'),(Opt 'Later' 'GRAY' 'Позже.'))
EnsureSelect 'Risk' @((Opt 'Critical' 'RED' 'Критический.'),(Opt 'High' 'ORANGE' 'Высокий.'),(Opt 'Medium' 'YELLOW' 'Средний.'),(Opt 'Low' 'GREEN' 'Низкий.'))
EnsureSelect 'Evidence' @((Opt 'Missing' 'RED' 'Evidence отсутствует.'),(Opt 'Partial' 'YELLOW' 'Evidence частичный.'),(Opt 'CI PASS' 'BLUE' 'CI PASS на точной revision.'),(Opt 'QA PASS' 'GREEN' 'Независимый QA PASS на точной revision.'))
EnsureIteration
EnsureItems
EnsureViews
Write-Host 'Project #2 настроен. Merge и QA PASS этот настройщик никогда не выполняет автоматически.'
