# Open-Vaultin

**Idioma:** [English](README.md) | **Português (Brasil)**

[![CI](https://github.com/CarlossgLuz/Open-Vaultin/actions/workflows/ci.yml/badge.svg)](https://github.com/CarlossgLuz/Open-Vaultin/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Licença MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

O **Open-Vaultin** é a distribuição open-source do Vaultin: uma camada local de governança e conhecimento durável para desenvolvimento de software com IA.

Ele centraliza agentes, skills, políticas, roteamento, histórico de execução, conhecimento dos projetos e evidências. A integração principal é com o Codex, por meio de plugin local e hooks de ciclo de vida. Outros clientes podem acessar ferramentas de conhecimento via MCP.

> **Estado: V1 inicial, anterior à versão 1.0.** O núcleo possui validação em Windows e Linux. A execução real dos hooks depende do cliente e da versão usados. Instalar arquivos de configuração não comprova que o cliente executa os hooks.

## O que ele faz na prática?

O cliente envia uma tarefa; o Vaultin carrega políticas, identifica o projeto, registra a execução e escolhe um fluxo/agente. Com uma chave TypeSafe, pode consultar o **JEV** para essa decisão. Sem a chave ou se a consulta falhar, usa roteamento determinístico. Durante a execução, os hooks disponíveis registram ações e evidências; ao finalizar, o Vaultin grava o resultado e o recibo local.

**O JEV auxilia o roteamento. As políticas continuam sendo a autoridade.** Ele não substitui o modelo do Codex nem libera ações proibidas.

Principais recursos:

- registro local e durável de execuções;
- integração com o ciclo de vida do Codex;
- recuperação de execuções interrompidas ou abandonadas;
- roteamento validado contra o catálogo de agentes e skills;
- contexto compacto para reduzir informações desnecessárias enviadas ao modelo;
- conhecimento canônico por projeto e mecanismos de sincronização com Git;
- recibos com evidências e estados explícitos de falha;
- interface MCP restrita e instaladores para Windows/Linux.

## Antes de começar

Instale no **computador e na conta do sistema que executam o Codex**. Instalar no Windows não configura automaticamente WSL, uma VM, container, servidor remoto ou sessão de navegador. Cada ambiente precisa da sua própria integração.

Você precisa de:

- Python **3.11 ou superior**, com suporte a venv e pip;
- Git;
- Windows ou Linux;
- um cliente Codex com suporte aos hooks usados pelo Vaultin;
- acesso ao índice de pacotes Python durante a instalação.

A chave TypeSafe é **opcional**. O Vaultin funciona com fallback determinístico sem ela.

Verifique no terminal:

Windows PowerShell:

```powershell
python --version
git --version
```

Linux Bash:

```bash
python3 --version
git --version
```

Se no Windows o Python só estiver disponível pelo comando `py`, use `py --version` e defina `$env:PYTHON = "py"` antes do instalador. Para Codex CLI, confira `codex --version` e conclua a autenticação do próprio Codex. O Vaultin não instala nem autentica esse cliente.

## 1. Prepare sua cópia pessoal

Para apenas avaliar, clone o repositório público:

```bash
git clone https://github.com/CarlossgLuz/Open-Vaultin.git
cd Open-Vaultin
```

Para uso pessoal com conhecimento privado, crie uma **cópia em um repositório privado independente**. Um fork de repositório público no GitHub é público; não conte com um “fork privado”.

1. No GitHub, crie um repositório chamado, por exemplo, `Vaultin-Personal`.
2. Marque **Private** e deixe-o vazio, sem README, licença ou `.gitignore` gerados.
3. Execute os comandos abaixo, trocando `octocat` pelo seu usuário e o nome do repositório pelo que você criou:

```bash
git clone https://github.com/CarlossgLuz/Open-Vaultin.git Vaultin-Personal
cd Vaultin-Personal
git remote rename origin upstream
git remote add origin https://github.com/octocat/Vaultin-Personal.git
git remote -v
git push -u origin main
```

Esses comandos funcionam em PowerShell e Bash. Quando necessário, autentique o Git pelo gerenciador de credenciais ou configure SSH. `origin` deve apontar para sua cópia privada; `upstream`, para o projeto público. Preserve a licença MIT. Referência: [duplicar um repositório no GitHub](https://docs.github.com/pt/repositories/creating-and-managing-repositories/duplicating-a-repository).

**Mantenha essa pasta em um local estável.** O instalador usa seu código diretamente. Mover ou excluir a pasta quebra os caminhos instalados; se mudar o local, execute novamente o instalador na nova pasta.

## 2. Edite o `vaultin.yaml`

Abra o arquivo **`vaultin.yaml` na raiz da pasta que acabou de clonar**, usando seu editor. Normalmente você só precisa ajustar dois campos:

```yaml
repository: octocat/Vaultin-Personal
project_vault_owner: octocat
```

`repository` é o repositório que guarda o **Vaultin**, não o repositório da aplicação em que você vai trabalhar. Se sua cópia se chama `Meu-Vaultin`, use `seu-usuario/Meu-Vaultin`.

Exemplo completo:

```yaml
version: 1
repository: octocat/Vaultin-Personal
project_vault_owner: octocat
project_vault_prefix: vault-
fail_closed: true
runtime_dir_name: .vaultin-runtime
```

| Campo | O que alterar | Para que serve |
|---|---|---|
| `version` | Mantenha `1` | Versão do formato de configuração. |
| `repository` | Seu `usuario/repositorio` real | Identificador do repositório canônico do Vaultin. |
| `project_vault_owner` | Seu usuário GitHub | Proprietário esperado para réplicas de vaults. O helper atual cria repositórios na conta pessoal autenticada via `/user/repos`; criação em organizações não está implementada nesse helper. |
| `project_vault_prefix` | Normalmente mantenha `vault-` | O projeto `example-api` terá uma réplica chamada `vault-example-api`. |
| `fail_closed` | Mantenha `true` | Intenção de governança; não garante que o cliente tenha uma barreira completa de aplicação das políticas. |
| `runtime_dir_name` | Mantenha `.vaultin-runtime` | Pasta de estado operacional local dentro da cópia do Vaultin. |

Para uma avaliação sem remoto próprio, use `CarlossgLuz/Open-Vaultin` como identificador e mantenha a publicação desabilitada.

O YAML rejeita campos desconhecidos. **Não adicione `api_key`, `token` ou `TYPESAFE_API_KEY` nele.** Para sua cópia privada, salve a configuração sem segredos:

```bash
git add vaultin.yaml
git commit -m "chore: configure personal Vaultin repository"
git push origin main
```

## 3. Configure o token do JEV / TypeSafe

**Onde colocar a chave?** Na variável de ambiente **`TYPESAFE_API_KEY` do ambiente que executa o Codex**. Os hooks herdam essa variável do processo do cliente.

O Vaultin **não carrega `.env` automaticamente**. Também não existe campo de token no `vaultin.yaml` ou nas configurações do plugin.

1. Acesse a [página de chaves da TypeSafe](https://console.typesafe.ai/keys), faça login e obtenha uma chave pelos controles disponíveis na sua conta. Confira acesso ao serviço e cobrança no painel.
2. Configure a variável seguindo as instruções do seu sistema abaixo.
3. Inicie/reinicie o Codex em um ambiente que realmente tenha recebido essa variável.

Use uma **chave da TypeSafe**, não um token GitHub nem uma credencial OpenAI/Codex. Informe a chave pura, sem escrever `Bearer ` antes dela. O adapter atual já adiciona o cabeçalho de autenticação e chama `https://api.typesafe.ai/v1/systemone` com o modelo `jev-latest`. Não precisa instalar um daemon JEV, SDK ou outro hook de roteamento para essa integração HTTP. Referência: [API oficial](https://api.typesafe.ai/redoc).

Com o JEV habilitado, o roteamento envia à TypeSafe o texto da tarefa, o diretório de trabalho e o identificador do projeto atual. Use uma tarefa sem informações sensíveis no teste.

### Windows: PowerShell, sessão atual e persistência

Execute em **PowerShell** e cole sua chave real no campo oculto. Assim, o valor não fica escrito no histórico do comando:

```powershell
$JevSecret = Read-Host "TypeSafe API key" -AsSecureString
$env:TYPESAFE_API_KEY = [System.Net.NetworkCredential]::new("", $JevSecret).Password
[Environment]::SetEnvironmentVariable("TYPESAFE_API_KEY", $env:TYPESAFE_API_KEY, "User")
Remove-Variable JevSecret
```

Isso configura o terminal atual e persiste a variável para seu usuário Windows. A variável persistida **não é um cofre criptografado**; não use esse método em uma conta compartilhada.

Feche completamente o Codex e abra novamente. Processos que já estavam abertos não recebem a mudança automaticamente. Para CLI, rode `codex` nesse mesmo PowerShell. Para aplicativo desktop, reinicie também o launcher/IDE que já estava aberto; se ainda herdar o ambiente antigo, saia da sessão do Windows e entre novamente.

Confira a presença sem mostrar o token:

```powershell
if ([string]::IsNullOrWhiteSpace($env:TYPESAFE_API_KEY)) {
    "TYPESAFE_API_KEY: ausente neste terminal"
} else {
    "TYPESAFE_API_KEY: configurada neste terminal"
}
```

### Linux Bash: terminal atual

```bash
read -rsp 'TypeSafe API key: ' TYPESAFE_API_KEY
printf '\n'
export TYPESAFE_API_KEY
```

Após instalar, execute `codex` nesse mesmo terminal. Ao fechar o shell, essa configuração deixa de existir nele. Um aplicativo já aberto não recebe a variável automaticamente.

### Linux Bash: persistência opcional

Para não informar a chave a cada novo terminal, crie um arquivo local protegido **fora do repositório**:

```bash
mkdir -p "$HOME/.config/vaultin"
touch "$HOME/.config/vaultin/jev.env"
chmod 600 "$HOME/.config/vaultin/jev.env"
```

Abra `~/.config/vaultin/jev.env` no editor e coloque esta linha, substituindo o exemplo pela sua chave real:

```bash
export TYPESAFE_API_KEY='COLE_SUA_CHAVE_REAL_DA_TYPESAFE_AQUI'
```

Carregue antes de iniciar o cliente:

```bash
source "$HOME/.config/vaultin/jev.env"
codex
```

Para terminais Bash interativos, você pode adicionar `source "$HOME/.config/vaultin/jev.env"` ao `~/.bashrc`. O arquivo contém texto puro protegido por permissões, não criptografia. Launchers desktop, serviços systemd, containers e WSL não carregam automaticamente seu `.bashrc`; configure a variável no launcher/serviço/ambiente correspondente. Para Zsh, adapte o arquivo de inicialização.

Confira sem exibir a chave:

```bash
if [ -n "${TYPESAFE_API_KEY:-}" ]; then
  printf 'TYPESAFE_API_KEY: configurada neste terminal\n'
else
  printf 'TYPESAFE_API_KEY: ausente neste terminal\n'
fi
```

**Você pode pular esta etapa.** Sem chave, o Vaultin usa fallback determinístico. A presença da variável não comprova que a chave é válida nem que uma chamada JEV funcionou.

## 4. Instale o Vaultin

Execute **na raiz da cópia do Vaultin**, não na pasta da aplicação.

Windows PowerShell:

```powershell
.\scripts\install.ps1
```

Linux Bash:

```bash
bash scripts/install.sh
```

Se o Windows bloquear a execução do script, revise seu conteúdo e a política da máquina antes de alterá-la. Em equipamento corporativo, siga a política da organização. No Linux, o Python precisa de suporte a venv/pip.

O instalador cria um ambiente isolado em `~/.vaultin/venv`, instala a cópia em modo editável, salva seu caminho absoluto em `~/.vaultin/root`, cria wrappers e registra plugin/hooks do Codex. No Windows, `~` representa a pasta do seu usuário.

| Local | O que é configurado |
|---|---|
| `~/.vaultin/root` | Caminho da pasta canônica do Vaultin. |
| `~/.vaultin/bin/` | Wrappers da CLI e dos hooks. |
| `~/.agents/plugins/marketplace.json` | Registro do plugin local. |
| `~/.codex/config.toml` | Ativação do plugin Vaultin. |
| `~/.codex/hooks.json` | Hooks do usuário, preservando grupos não relacionados. |
| `~/.codex/plugins/vaultin/` | Arquivos do plugin local. |

O instalador substitui a pasta/cache do plugin Vaultin e termina com a checagem de saúde do núcleo. Não salva a chave TypeSafe, não instala o Codex, não autentica GitHub e não configura automaticamente outros clientes.

O helper atual de hooks no Windows rejeita um caminho de wrapper com espaços, por exemplo quando a pasta do perfil de usuário tem espaços no nome. Esse erro representa um caminho não suportado; não considere a instalação concluída.

## 5. Valide o núcleo instalado

Ainda na **pasta do Vaultin**:

```text
vaultinctl health
vaultinctl doctor
vaultinctl status
```

Se o comando não estiver disponível, use o caminho real instalado.

Windows PowerShell:

```powershell
& "$HOME\.vaultin\bin\vaultinctl.cmd" health --root (Get-Location).Path
& "$HOME\.vaultin\bin\vaultinctl.cmd" doctor --root (Get-Location).Path
& "$HOME\.vaultin\bin\vaultinctl.cmd" status --root (Get-Location).Path
```

Linux Bash:

```bash
"$HOME/.vaultin/bin/vaultinctl" health --root "$PWD"
"$HOME/.vaultin/bin/vaultinctl" doctor --root "$PWD"
"$HOME/.vaultin/bin/vaultinctl" status --root "$PWD"
```

No Windows, o instalador adiciona a pasta dos wrappers ao PATH do usuário e do terminal atual. No Linux, cria um link em `~/.local/bin`; essa pasta precisa estar no PATH para usar o comando curto.

| Comando | O que verifica hoje |
|---|---|
| `health` | Configuração, código ativo, políticas, workflow, agentes, skills e ledger. O resultado geral esperado é `PASS`. |
| `doctor` | Exibe o código/root ativos e executa as mesmas verificações de saúde do núcleo. |
| `status` | Executa as verificações do núcleo e mostra `pending_sync`. |

**Esses comandos não validam o token TypeSafe, autenticação GitHub nem execução real dos hooks pelo Codex.** Por padrão, `--root` é o diretório atual. Se estiver na pasta da aplicação, informe explicitamente o caminho absoluto da **cópia do Vaultin**, não o da aplicação.

## 6. Use em uma sessão real do Codex

1. Reinicie completamente o Codex após instalar.
2. Confira se o plugin Vaultin está habilitado e revise/confie nos hooks locais quando o cliente solicitar.
3. Abra o repositório da aplicação em que deseja trabalhar. Mantenha a cópia do Vaultin no local original.
4. No Codex CLI, entre na pasta dessa aplicação e rode `codex` pelo terminal que recebeu `TYPESAFE_API_KEY`.
5. Envie uma tarefa inofensiva: **“Explique a estrutura deste repositório sem editar arquivos.”**

O wrapper instalado já fixa a cópia do Vaultin com `--root`. O diretório de trabalho da sessão identifica a aplicação. Não é necessário copiar YAML, token ou hooks para cada projeto.

Os eventos instalados são `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, `Interrupt` e `SessionEnd`. O suporte real depende do cliente. Uma instalação no seu PC não conecta automaticamente uma sessão remota ou de navegador.

## 7. Confirme que o JEV foi realmente usado

Depois da tarefa de teste, volte à **pasta do Vaultin** em outro terminal. Leia o último evento de roteamento do ledger. O código abaixo não imprime a chave nem o texto da tarefa.

Windows PowerShell:

```powershell
@'
import json, sqlite3
from pathlib import Path
from vaultin.paths import VaultinPaths
path = VaultinPaths.from_root(Path.cwd()).ledger_db
with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
    row = db.execute("SELECT execution_id, payload_json FROM events WHERE kind = 'ROUTED' ORDER BY created_at DESC, sequence DESC LIMIT 1").fetchone()
if row is None:
    print("Sem evento de roteamento: confira a execucao dos hooks no cliente.")
else:
    route = json.loads(row[1])
    print("execution_id:", row[0])
    print("source:", route.get("source"))
    print("fallback_reason:", route.get("fallback_reason"))
'@ | & "$HOME\.vaultin\venv\Scripts\python.exe" -
```

Linux Bash:

```bash
"$HOME/.vaultin/venv/bin/python" - <<'PYTHON'
import json, sqlite3
from pathlib import Path
from vaultin.paths import VaultinPaths
path = VaultinPaths.from_root(Path.cwd()).ledger_db
with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
    row = db.execute("SELECT execution_id, payload_json FROM events WHERE kind = 'ROUTED' ORDER BY created_at DESC, sequence DESC LIMIT 1").fetchone()
if row is None:
    print("Sem evento de roteamento: confira a execucao dos hooks no cliente.")
else:
    route = json.loads(row[1])
    print("execution_id:", row[0])
    print("source:", route.get("source"))
    print("fallback_reason:", route.get("fallback_reason"))
PYTHON
```

| Resultado | Interpretação / próximo passo |
|---|---|
| `source: jev` | O JEV retornou uma rota aceita pelo Vaultin nessa execução. |
| `source: fallback` | Foi usado roteamento determinístico; leia o motivo. Isso sozinho não significa falha de governança. |
| `source: explicit` | Uma diretiva suportada `workflow=...` escolheu o fluxo antes do JEV. Retire a diretiva para testar o JEV. |
| `jev_http_error` | Falha HTTP, de rede ou timeout. O adapter não expõe o status HTTP; confira chave/conta TypeSafe, conectividade e timeout. |
| `jev_schema_error` | A resposta não correspondeu ao contrato esperado pelo adapter. |
| `low_agent_confidence` / `low_workflow_confidence` | O JEV respondeu, mas a confiança exigida foi insuficiente. |
| Sem evento / ledger ausente | O prompt pode não ter passado pelos hooks, falhado antes do roteamento ou você pode estar lendo outra cópia. Confira a saída dos hooks e `~/.vaultin/hook-errors.log`, se existir. |

Em sessões simultâneas, o último evento pode ser de outra execução; compare o `execution_id`. **`health: PASS` não comprova integração JEV.**

## 8. GitHub e integração com outros clientes

O JEV precisa de `TYPESAFE_API_KEY`. Push/pull comuns precisam das credenciais do Git. O helper opcional que cria réplicas privadas usa uma variável separada, **`GITHUB_TOKEN`**, com permissões para essa operação na conta pessoal autenticada. Login do Git não configura essa variável automaticamente. O YAML também não cria repositórios sozinho.

Não habilite publicação só para testar a instalação. Recibos ficam locais por padrão (`VAULTIN_PUBLISH_RECEIPTS` ausente), e publicação via MCP também fica desabilitada (`VAULTIN_MCP_ALLOW_PUBLISH` ausente). Revise conhecimento e metadados antes de publicar.

Para outro cliente que suporte **MCP via stdio**, configure o comando do servidor como o executável absoluto:

- Windows: `C:\Users\SEU_USUARIO\.vaultin\venv\Scripts\vaultin-mcp.exe`
- Linux: `/home/SEU_USUARIO/.vaultin/venv/bin/vaultin-mcp`

Sem argumentos adicionais, o servidor usa o root registrado pelo instalador. O cliente inicia o processo; o local de configuração e o formato JSON dependem desse cliente. O instalador não adiciona o executável MCP ao PATH.

O MCP oferece `search_knowledge`, `read_canonical`, `write_project_note` e `inspect_registry`. Leituras são limitadas às superfícies canônicas permitidas; notas são Markdown em vaults de projetos existentes. Publicação exige opt-in explícito. Isso **não instala os hooks do Codex nem roteia automaticamente cada prompt desse outro cliente pelo JEV**. Consulte [integrações](docs/client-integrations.md).

## 9. Atualize ou desative

Na cópia privada, busque as atualizações públicas, revise-as e resolva conflitos com sua configuração:

```bash
git fetch upstream
git merge upstream/main
```

Execute novamente o instalador se mudarem dependências, wrappers ou definições de hooks. Reinicie o Codex e repita as verificações do núcleo e da sessão real.

Para desabilitar o JEV no Windows:

```powershell
Remove-Item Env:TYPESAFE_API_KEY -ErrorAction SilentlyContinue
[Environment]::SetEnvironmentVariable("TYPESAFE_API_KEY", $null, "User")
```

No Linux, execute `unset TYPESAFE_API_KEY` e remova o export/carregamento do arquivo local ou de inicialização. Reinicie o cliente. O fallback determinístico continua disponível. Revogue a chave no painel TypeSafe se quiser invalidar a credencial.

Não existe desinstalador automático atualmente. Para desativar o Vaultin inteiro, remova apenas os grupos de hooks cujos comandos contêm `vaultinctl-hook` em `~/.codex/hooks.json`, desative a entrada do plugin Vaultin em `~/.codex/config.toml` e reinicie o Codex. Faça backup da configuração antes de editar e preserve outros plugins/hooks. Desativar só o plugin pode deixar os hooks do usuário ativos.

## Variáveis de ambiente

| Variável | Quando usar |
|---|---|
| `TYPESAFE_API_KEY` | Chave TypeSafe para roteamento JEV, herdada pelo cliente/hooks. |
| `VAULTIN_JEV_TIMEOUT_SECONDS` | Timeout do JEV nos hooks: padrão 3 segundos, limitado entre 0,5 e 5. |
| `VAULTIN_ROOT` | Root alternativo quando não há `--root` explícito. O wrapper instalado já usa `--root`. |
| `GITHUB_TOKEN` | Autenticação do helper opcional para criação de réplicas privadas. |
| `VAULTIN_PUBLISH_RECEIPTS` | Opt-in para publicação de recibos Git; desabilitado por padrão. |
| `VAULTIN_MCP_ALLOW_PUBLISH` | Opt-in para publicação Git pelo MCP; desabilitado por padrão. |
| `PYTHON` | Interpretador usado pelo instalador, compatível com Python 3.11+. |

O JEV usa decisões tipadas de agente/fluxo/skills; o Codex recebe contexto compacto validado. Erros ou confiança insuficiente levam ao fallback. Referência completa: [configuração](docs/configuration.md).

## Privacidade e segurança

`memory/` e `.vaultin-runtime/` são ignorados pelo Git. Recibos e publicações MCP ficam locais por padrão. Conhecimento durável pode conter dados privados mesmo quando não há tokens; mantenha sua cópia privada.

Não publique chaves, senhas, nomes de repositórios privados, caminhos sensíveis, prompts privados ou conhecimento proprietário. Não grave tokens em YAML, perfis de agentes, skills, notas ou recibos. Para vulnerabilidades, siga [SECURITY.md](SECURITY.md).

## Organização do projeto

| Caminho | Conteúdo |
|---|---|
| `.agents/skills/` | Catálogo de skills. |
| `agents/` | Perfis e registro de agentes. |
| `policies/` | Políticas de governança. |
| `workflows/` | Estados e fluxos de execução. |
| `src/vaultin/` | Implementação do núcleo. |
| `adapters/` | Integrações com clientes. |
| `scripts/` | Instaladores Windows/Linux. |
| `vaults/` | Registro e conhecimento canônico por projeto. |
| `knowledge/` | Conhecimento global durável. |
| `docs/` | Documentação técnica e operacional. |
| `tests/` e `evals/` | Testes e avaliações de comportamento. |

O conhecimento de projeto canônico fica em `vaults/projects/<project-slug>/`. Réplicas não são o local principal de edição. O estado operacional local não substitui a documentação durável.

## Solução de problemas

Comece pela etapa 5, usando o root correto. Depois confira:

- Python/Git e suporte a venv/pip;
- os dois campos configurados no YAML;
- o caminho salvo em `~/.vaultin/root` e a pasta original ainda existente;
- reinício do cliente e confiança nos hooks;
- se o processo que lança o Codex recebeu a variável, não apenas outro terminal;
- a origem/motivo da rota no ledger, conforme etapa 7;
- saída dos hooks e `~/.vaultin/hook-errors.log`, se criado.

Mais casos: [troubleshooting](docs/troubleshooting.md). Se for enviar um diagnóstico, remova segredos e informações privadas dos logs.

## Documentação e desenvolvimento

Este README contém o fluxo completo em português. A documentação técnica vinculada abaixo está atualmente em inglês:

- [Primeiros passos](docs/getting-started.md)
- [Configuração](docs/configuration.md)
- [Integrações com clientes](docs/client-integrations.md)
- [Arquitetura](docs/architecture.md)
- [Instalação](docs/operations/install.md)
- [Recuperação](docs/operations/recovery.md)
- [Roadmap](ROADMAP.md)
- [Processo de releases](docs/releasing.md)

Para desenvolvimento, em um ambiente Python adequado:

```bash
python -m pip install -e ".[dev]"
pytest
```

O CI oficial valida Windows e Linux. Antes de contribuir, leia [CONTRIBUTING.md](CONTRIBUTING.md), retire dados privados dos exemplos/logs, execute os testes e mantenha a documentação coerente com o código. Ao alterar o fluxo de instalação, atualize as versões inglesa e PT-BR.

## Licença

Distribuído sob a **licença MIT**. Consulte [LICENSE](LICENSE).
