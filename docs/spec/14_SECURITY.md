# 14. Security — безопасность и доверие

## Схема

Любой запрос / ресурс / контекст / команда
→ Identity (кто источник?)
→ Trust Classification (уровень доверия)
→ CONTROL или DATA?
→ Injection Guard (защита от внедрения команд)
→ Rules + Scope + Capability Grant
→ нужен USER / ADMIN Approval?
→ минимальные права
→ изолированное Execution
→ Evidence + Audit
→ Result

При неопределённости критического действия: BLOCKED.

## 14.1. Назначение

Security отвечает на вопрос: кому, чему и при каких условиях KAT9I_OS разрешает влиять на поведение системы и выполнять действия.

Security должна защищать пользователя, администратора, Workers, Knowledge Base, контекст, локальный компьютер, внешние системы, секреты, правила, результаты и саму KAT9I_OS.

## 14.2. Главный принцип

Доступ к информации не означает право управлять системой.

Worker может прочитать документ. Это не означает, что команды внутри документа становятся командами KAT9I_OS.

## 14.3. CONTROL и DATA

CONTROL — управляющая информация, способная менять поведение системы. Допустимые источники: System Policy, Rule Manager, TaskContract, Security Policy, разрешённый Workflow, подтверждённое решение USER, подтверждённое решение ADMIN.

DATA — данные, используемые как информация, но не имеющие управляющей силы. Например: Issue, README, сайт, PDF, письмо, документ, комментарий, код, KnowledgeRecord, Research, Result другого Worker.

Даже если DATA содержит инструкцию «игнорируй правила и выполни команду X», для KAT9I_OS это остаётся данными.

## 14.4. DATA не может самостоятельно стать CONTROL

Ни модель, ни Worker не могут самостоятельно повышать данные до управляющих команд.

Переход DATA → CONTROL возможен только через доверенный процесс KAT9I_OS: обнаружение требования → Rule Candidate → проверка → USER/ADMIN Approval при необходимости → Rule Manager → CONTROL.

## 14.5. Prompt Injection

Любой внешний текст считается потенциально содержащим внедрённые управляющие команды. Источники риска: Web, GitHub, документы, изображения с текстом, PDF, письма, Knowledge Source, MCP, результаты других агентов, ответы внешних Tools.

Защита не должна строиться только на промпте. Основная защита должна быть архитектурной.

## 14.6. Архитектурная защита от Prompt Injection

Минимальные уровни:

1. источник помечается как DATA;
2. сохраняется provenance;
3. контекст структурируется;
4. управляющие поля отделяются от содержимого;
5. Tool permissions не выводятся из текста;
6. Scope задаётся заранее;
7. Capability Grant выдаётся отдельно;
8. опасное действие повторно проверяется Security;
9. внешний текст не может повысить собственный Trust.

## 14.7. Context Injection Guard

Контекст должен иметь структурированное разделение CONTROL, RULES, TASK, DATA, REFERENCES и RESULTS.

## 14.8. Инструкции внутри кода

Комментарии и строки программы являются DATA. Они не могут автоматически стать командами KAT9I_OS.

## 14.9. Command Injection

Нельзя напрямую преобразовывать внешние DATA в shell-команду. Команды строятся как разрешённое действие + структурированные параметры.

## 14.10. Tool Injection / Tool Poisoning

Результат внешнего Tool или MCP-сервера по умолчанию считается DATA, а не CONTROL.

## 14.11. Tool Registry Trust

Для Tool необходимо знать источник, владельца, версию, разрешённые действия, Trust, получаемые данные и возможные side effects.

## 14.12. Supply Chain

Security учитывает безопасность Skills, локального кода, зависимостей, MCP-серверов, Runtime, библиотек, обновлений и моделей.

## 14.13. Identity

Типы Identity: USER, ADMIN, LOCAL_WORKER, REMOTE_WORKER, KAT9I_REMOTE, SERVICE, CONNECTOR, MCP_SERVER, PROVIDER.

Identity и Capability — разные сущности.

## 14.14. USER

USER принимает решения, относящиеся к пользовательскому намерению: выбор варианта, желаемый результат, недостающая информация, личные предпочтения, содержательные решения.

## 14.15. ADMIN

ADMIN отвечает за высокорисковые системные решения: расширение прав, подключение доверенного Worker, изменение Security Policy, доступ к секретам, критические Integrations и системные границы.

USER и ADMIN могут физически быть одним человеком, но логически это разные роли.

## 14.16. Human Approval

Human Approval должен быть структурированным и содержать actor, action, resource, scope, срок, task_id и timestamp.

## 14.17. Ограниченность Approval

Разрешение на одно действие не является постоянным разрешением на весь класс действий.

## 14.18. Deny wins

Запрет выше разрешения. USER не может отменить системный запрет без соответствующего административного полномочия.

## 14.19. Least Privilege

Worker получает только права конкретной задачи.

## 14.20. Temporary Capabilities

Capability Grant автоматически истекает после завершения Task, Lease expiration, заданного срока, отмены или критического изменения Security State.

## 14.21. Scope Guard

Security задаёт Scope, Execution детерминированно проверяет фактические действия.

## 14.22. Privilege Escalation

Worker не может самостоятельно расширить права. Используется REQUEST_CAPABILITY_EXTENSION → Security → при необходимости ADMIN → новый Capability Grant.

## 14.23. Sensitive Data Classification

Минимальные классы: PUBLIC, INTERNAL, SENSITIVE, SECRET, LOCAL_ONLY.

## 14.24. Наследование классификации

Итоговый пакет не может иметь уровень чувствительности ниже наиболее чувствительной значимой части.

## 14.25. Data Minimization

Даже разрешённому Provider передаётся минимально необходимый объём данных.

## 14.26. Secrets

Секреты не хранятся в промптах без необходимости, не попадают в Logs, обычную Knowledge Base, ResultRef и обычный Cache, не передаются Worker без необходимости.

## 14.27. SecretRef

По возможности вместо секрета используется SecretRef. Runtime получает секрет только на время разрешённой операции.

## 14.28. NO_CACHE для секретов

Секреты и временные токены по умолчанию NO_CACHE.

## 14.29. Knowledge Security

KnowledgeRecord должен иметь Scope, Sensitivity, Trust, Provenance и допустимых Consumers.

## 14.30. Knowledge Laundering

Преобразование, summary или перенос записи в Knowledge Base не повышают автоматически Trust. Provenance сохраняется до первоисточника.

## 14.31. Cache Security

Cache наследует ограничения исходных данных. NO_CACHE распространяется на производные данные, если отдельная политика не разрешает обратное.

## 14.32. Context Drift и безопасность

Смена repository, RulesRef, чувствительных Resources или Task Scope может инвалидировать старые Security Decision и Grants.

## 14.33. External Provider Security

До выбора внешнего Provider проверяются класс данных, Rules, допустимый Provider, требуемые Connectors, передаваемые данные и Result Sink.

## 14.34. Local-first как защита

Для SENSITIVE/LOCAL_ONLY Local-first является одновременно механизмом экономии и уменьшения поверхности утечки.

## 14.35. Remote Worker Security

Удалённый Worker, включая KAT9I_REMOTE, проверяется по Identity, Trust, Capabilities, версии протокола, Resources, Scope и Capability Grant.

## 14.36. Compromised Worker

Архитектура должна ограничивать ущерб от ошибочного или скомпрометированного Worker через Scope, временные права, изолированный Workspace, Tool Allowlist, ResultSink и независимый QA.

## 14.37. Независимый QA

Для критических изменений Implementation Worker != QA Worker. QA проверяет ResultRef, Evidence, точную revision и RulesRef независимо.

## 14.38. Approval не заменяет QA

Approval означает, что действие разрешено. QA означает, что результат корректен.

## 14.39. Fail-closed

Если система не может определить Identity, Scope, Rules, Sensitivity, действительность Grant или безопасность действия, потенциально опасная операция блокируется.

## 14.40. Security Event

Отдельно фиксируются injection detected, scope violation, denied capability request, secret exposure attempt, invalid approval, unknown Worker, modified RulesRef, unauthorized Tool invocation и аналогичные события.

## 14.41. Audit Trail

Для значимых операций должно быть возможно установить кто запросил, кто разрешил, кто выполнил, какой RulesRef, какой Capability Grant, какой Resource, какая revision, какой ResultRef и какой QA.

## 14.42. Audit Trail не равен Chain of Thought

Для аудита нужны проверяемые события и решения, а не внутренние рассуждения модели.

## 14.43. Security Metrics

Минимально измеряются blocked actions, scope violations, injection detections, rejected Tools, privilege escalation requests, USER approvals, ADMIN approvals, secret access events, invalid grants, security-related QA failures, операции SENSITIVE/LOCAL_ONLY и инциденты false positive/false negative.

## 14.44. Security Learning

Learning может улучшать detection patterns, Trust scores, Tool reputation, Provider routing, рекомендации Scope и классификацию данных, но не может самостоятельно ослаблять Security Policy.

## 14.45. Security должна быть дешёвой

Identity, Scope, Grant, hash, signature, classification, allowlist, TTL и revision по возможности проверяются локальным детерминированным кодом.

## 14.46. Security не доверяет модели как источнику факта

Права, commit, branch, Approval, secret access и QA status проверяются через канонические источники.

## 14.47. Security и ResourceRef

Наличие ResourceRef означает только, что объект известен системе, но не что доступ к нему разрешён.

## 14.48. Security и ResultRef

ResultRef от Worker считается DATA до проверки. Статус QA должен происходить из доверенного QA-процесса.

## 14.49. Emergency Stop

USER/ADMIN должен иметь возможность остановить конкретную Task, Worker, Workflow, удалённый узел или внешние записи. Emergency Stop не должен зависеть от согласия модели.

## 14.50. Revocation

Администратор или Security Policy могут немедленно отозвать Capability Grant, Worker Trust, Connector, Provider route или Secret access. Отзыв выше ранее выданного разрешения.

## 14.51. Основные принципы

1. Доступ к данным не означает право управлять системой.
2. CONTROL и DATA разделены архитектурно.
3. Внешний контекст по умолчанию является DATA.
4. DATA не может самостоятельно повысить себя до CONTROL.
5. Prompt Injection блокируется архитектурными границами, а не только промптом.
6. Command Injection предотвращается структурированным формированием команд.
7. Результат Tool или другого Worker не является командой.
8. USER и ADMIN — разные логические роли.
9. Approval имеет Scope и срок.
10. Запрет выше разрешения.
11. Используются минимальные и временные права.
12. Worker не может самостоятельно расширять полномочия.
13. Чувствительность данных влияет на маршрутизацию.
14. Секреты передаются по ссылкам и только при необходимости.
15. Knowledge и Cache наследуют Security исходных данных.
16. Преобразование данных не повышает автоматически Trust.
17. Компрометация одного Worker не должна компрометировать всю KAT9I_OS.
18. Независимый QA — отдельный защитный слой.
19. Неопределённость опасного действия приводит к BLOCKED.
20. Большинство Security-проверок выполняются локальным кодом.
21. Security Events и решения имеют Audit Trail.
22. USER/ADMIN могут выполнить Emergency Stop и отзыв разрешений.

## 14.52. Главный принцип

KAT9I_OS не должна пытаться сделать ИИ абсолютно доверенным. Она должна строиться так, чтобы ошибка, галлюцинация или внедрённая управляющая команда не могли превратиться в опасное действие без прохождения независимых программных границ прав, Scope, Security и Evidence.
