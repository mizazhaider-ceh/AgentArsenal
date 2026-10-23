![AgentArsenal](../assets/banner-keeper.png)

# AgentArsenal

<!-- SKILLCOUNT:START -->
![skills](https://img.shields.io/badge/skills-246-blue)
<!-- SKILLCOUNT:END -->
[![sub-skills](https://img.shields.io/badge/sub--skills-110-9cf)](../MINDMAP.md)
[![agents](https://img.shields.io/badge/agents-25-blueviolet)](../agents/README.md)
[![brains](https://img.shields.io/badge/brains-16-red)](../brains/README.md)
[![platforms](https://img.shields.io/badge/platforms-19-orange)](../platforms/PLATFORM_SUPPORT.md)
[![tools](https://img.shields.io/badge/CLI%20tools-47-yellow)](../tools/README.md)
[![quality](https://img.shields.io/badge/avg%20quality-95.6-success)](../scores.json)
[![validation](https://img.shields.io/badge/validation-passing-brightgreen)](../scripts/validate.py)
[![license](https://img.shields.io/badge/license-MIT-green)](../LICENSE)

**AgentArsenal est un dépôt unifié de skills pour agents qui creuse l'art de l'ingénierie logicielle et la pratique de la sécurité offensive, avec une qualité imposée par des machines, pas par l'intuition.**

Chaque skill porte une version, une date de fraîcheur et un état de cycle de vie. Un harnais CI à 14 contrôles et un scoreur de qualité de 0 à 100 maintiennent la barre haute. Un seul manifeste pilote l'installateur, le site de documentation et l'intégration au marketplace de Claude Code.

```diff
+ 246 skills dans 28 domaines, chacune versionnée, notée et vérifiée par la CI
+ 110 sous-skills qui creusent les 30 skills parentes à plus haute valeur
+ 25 agents nommés, 16 cerveaux de raisonnement, 8 playbooks d'engagement, 4 workflows multi-agents
+ 47 outils CLI en bibliothèque standard uniquement, zéro dépendance tierce
+ 19 plateformes d'agents supportées avec un seul standard SKILL.md
- Pas d'articles de blog épars, pas d'extraits non testés, pas de prompts jetables et périmés
```

![Statistiques AgentArsenal](../assets/stats-strip.svg)

## Table des matières

- [Qu'est-ce qu'AgentArsenal](#quest-ce-quagentarsenal)
- [Pour qui](#pour-qui)
- [Fonctionnement](#fonctionnement)
- [Démarrage rapide](#démarrage-rapide)
- [Installation pour votre plateforme](#installation-pour-votre-plateforme)
- [Référence des commandes](#référence-des-commandes)
- [Catalogue des skills](#catalogue-des-skills)
- [Sous-skills](#sous-skills)
- [Agents](#agents)
- [Cerveaux](#cerveaux)
- [Système de mémoire](#système-de-mémoire)
- [Documents de décision](#documents-de-décision)
- [Playbooks](#playbooks)
- [Workflows](#workflows)
- [Outils CLI](#outils-cli)
- [Qualité et benchmarks](#qualité-et-benchmarks)
- [Parcours d'apprentissage](#parcours-dapprentissage)
- [FAQ](#faq)
- [Statistiques du projet](#statistiques-du-projet)
- [Feuille de route](#feuille-de-route)
- [Contribuer](#contribuer)
- [Licence](#licence)
- [Remerciements](#remerciements)

## Qu'est-ce qu'AgentArsenal

AgentArsenal est une bibliothèque curée de **skills** pour agents de code IA, plus la machinerie qui les rend dignes de confiance : des **agents** (opérateurs nommés), des **cerveaux** (schémas de raisonnement réutilisables), des **sous-skills** (modules d'approfondissement), des **playbooks** (guides d'engagement de bout en bout), des **workflows** (schémas de coordination multi-agents), des **documents de décision** (politique d'escalade et de risque), un **système de mémoire** (schéma plus un CLI SQLite) et **47 outils CLI** (utilitaires d'opérateur en bibliothèque standard uniquement).

Une skill est un dossier contenant un fichier `SKILL.md`. Le fichier commence par un frontmatter YAML dont le champ `description` est un **déclencheur** : un paragraphe dense qui dit exactement quand l'agent doit charger la skill ("Use when ..."). Le corps donne ensuite à l'agent un Quick Workflow numéroté, des procédures par phase avec des commandes exactes, des cas limites, des chemins d'escalade, le point de vue du défenseur et des références clés. Les fichiers d'accompagnement suivent : `scripts/` pour le code exécutable, `references/` pour la documentation approfondie, `assets/` pour les modèles. Ils ne se chargent que lorsque le corps de la skill les mentionne.

Ce qui distingue ce dépôt d'un dossier de prompts :

- **Versionnage par skill.** Chaque skill porte un semver plus une entrée de changelog. Vous pouvez épingler `web-sqli@1.0.0` et savoir exactement ce que vous avez installé.
- **Qualité imposée par les machines.** `scripts/validate.py` exécute 14 contrôles en CI (standard de frontmatter, règles de nommage, acyclicité des dépendances, dates de fraîcheur). `scripts/score.py` note chaque skill de 0 à 100 sur la densité des déclencheurs, la qualité des commandes, les cas limites et les références. Fusionner exige 70 ou plus. La moyenne du dépôt est de 95,6 et l'artefact le moins bien noté est à 92.
- **Graphe de dépendances.** Les skills déclarent des arêtes `requires`, `extends` et `relates`. L'installateur résout automatiquement toute la fermeture de dépendances, et la CI échoue sur les références pendantes ou les cycles. Le graphe est visualisé dans [MINDMAP.md](../MINDMAP.md) et `docs/graph.html`.
- **Suivi de fraîcheur.** Chaque skill porte une date `last_verified`. La CI signale les dates impossibles ou périmées, pour que les skills obsolètes ne puissent pas se cacher.
- **États de cycle de vie.** Les skills sont `experimental`, `stable` ou `deprecated`. Les dépréciées restent lisibles mais sont exclues des nouveaux paquets.
- **Paquets hors ligne.** `scripts/bundle.py` empaquette les skills en une seule archive portable avec manifeste pour les environnements isolés.
- **Retour en arrière.** Chaque release est un tag git plus une entrée de changelog, et `install.sh` sauvegarde la cible avant d'y toucher. Une skill défectueuse se révoque proprement.
- **Manifeste de marketplace.** `.claude-plugin/marketplace.json` expose chaque skill directement à Claude Code.

![Fonctionnement d'AgentArsenal](../assets/how-it-works-strip.svg)

![AgentArsenal face aux dépôts de skills typiques](../assets/comparison-strip.svg)

| Capacité | AgentArsenal | Dépôt de skills typique |
| --- | --- | --- |
| Versionnage par skill | :white_check_mark: Semver plus entrée de changelog sur chaque skill | :x: Pas de suivi de version |
| Harnais de test | :white_check_mark: Harnais CI à 14 contrôles (`scripts/validate.py`) | :x: Pas de contrôles automatisés |
| Scores de qualité | :white_check_mark: 0 à 100 par skill, fusion exige 70+ | :x: Pas de notation |
| Graphe de dépendances | :white_check_mark: Relations validées et visualisées | :x: Pas de modèle de dépendances |
| Suivi de fraîcheur | :white_check_mark: Dates `last_verified`, la CI signale les périmées | :x: Pas de données de fraîcheur |
| États de cycle de vie | :white_check_mark: experimental, stable, deprecated | :x: Pas d'états de cycle de vie |
| Paquets hors ligne | :white_check_mark: Paquets portables en une archive avec manifeste | :x: Pas d'empaquetage |
| Retour en arrière | :white_check_mark: Tags git plus entrées de changelog par release | :x: Pas de discipline de release |
| Manifeste de marketplace | :white_check_mark: Intégration directe au marketplace de Claude Code | :x: Pas d'intégration marketplace |

## Pour qui

Guide complet des audiences : [AUDIENCES.md](../AUDIENCES.md). Chaque nom ci-dessous est un artefact réel de ce dépôt. Installez les démarreurs avec l'installateur sélectif, par exemple `./install.sh --version nmap-methodology@1.0.0` ou `./install.sh --category web`.

### :mortar_board: Étudiants en cybersécurité
**Ce que vous obtenez :** un parcours structuré des fondamentaux jusqu'à une méthodologie complète, chaque procédure écrite en étapes d'opérateur numérotées avec des commandes exactes. Les skills remplacent les articles de blog épars par une seule source curée déjà notée par un scoreur de qualité.
**Commencez par :** skills `recon-passive`, `recon-active`, `nmap-methodology`, `linux-hardening`, `web-sqli`, `webapp-pentest-methodology`, `python-cli-tooling`, `git-workflows` ; agent `recon-agent` ; cerveau `scientific-debugging`.

### :crossed_swords: Pentesters
**Ce que vous obtenez :** une méthodologie d'engagement complète, de la reco au rapport, avec une installation consciente des dépendances (la chaîne `requires` d'une skill s'installe automatiquement) et des chemins d'escalade quand la voie standard échoue.
**Commencez par :** skills `webapp-pentest-methodology`, `ad-enumeration`, `bloodhound-methodology`, `privesc-linux`, `privesc-windows`, `network-pivoting`, `c2-fundamentals`, `password-attacks`, `api-security-testing` ; agents `recon-agent`, `web-exploitation-agent`, `pentest-reporter-agent`.

### :rotating_light: Analystes SOC
**Ce que vous obtenez :** des runbooks de triage, du contenu de détection et des procédures DFIR écrites en checklists que votre agent peut exécuter pendant un shift en direct.
**Commencez par :** skills `siem-detections`, `sigma-rules`, `suricata-ids`, `threat-hunting`, `dfir-timeline`, playbook `soc-triage-day` ; agent `soc-analyst-agent` ; cerveau `opa-decision-loop`.

### :computer: Développeurs
**Ce que vous obtenez :** des skills d'artisanat logiciel qui font de votre agent un meilleur pair programmeur : code sécurisé, revue de code, méthodologie de débogage, CI/CD, conteneurs et stratégies de test.
**Commencez par :** skills `secure-coding`, `code-reviewer`, `debugging-methodology`, `git-workflows`, `docker-deep`, `testing-strategies` ; agent `code-review-agent` ; cerveau `scientific-debugging`.

### :microscope: Chercheurs en sécurité
**Ce que vous obtenez :** de la matière approfondie sur l'exploitation de binaires, la cryptographie, le matériel et la sécurité de l'IA, avec références et cas limites au lieu de résumés superficiels.
**Commencez par :** skills `pwn-fundamentals`, `rop-chains`, `heap-exploitation`, `ghidra-basics`, `rsa-attacks`, `llm-red-teaming` ; agent `binary-exploitation-agent` ; cerveau `hypothesis-driven-testing`.

### :teacher: Enseignants
**Ce que vous obtenez :** une colonne vertébrale de cursus prête à l'emploi. Les [parcours d'apprentissage](../docs/learning-paths/BEGINNER.md) ordonnent les skills de débutant à expert, et chaque skill a le même squelette de corps (Quick Workflow, Edge cases, Key references) pour que les plans de cours s'écrivent tout seuls.
**Commencez par :** les domaines `recon` et `network`, le cerveau `scientific-debugging` et le playbook `soc-triage-day` pour les labs blue team.

### :moneybag: Chasseurs de bug bounty
**Ce que vous obtenez :** un workflow de chasse systématique et des modèles de rapports qui sont acceptés et payés, plus les skills d'attaque web et API qui couvrent les cibles les plus courantes.
**Commencez par :** skills `bug-bounty-workflow`, `webapp-pentest-methodology`, `api-security-testing`, `recon-active` ; agent `bug-bounty-hunter-agent` ; playbook `bug-bounty-sprint`.

### :shield: Blue teams
**Ce que vous obtenez :** ingénierie de détection, baselines de durcissement, playbooks d'incident et exercices de purple team qui prouvent que les détections fonctionnent au lieu de le supposer.
**Commencez par :** skills `detection-as-code`, `sigma-rules`, `endpoint-hardening-baseline`, `incident-playbooks`, `purple-team-exercises` ; agent `purple-team-agent` ; cerveau `defender-mindset`.

### :rocket: Fondateurs de startups
**Ce que vous obtenez :** une baseline de sécurité pragmatique sans embaucher d'équipe : déploiement SDLC, revue cloud, gestion des secrets et ingénierie de la confidentialité, à la taille des petites équipes.
**Commencez par :** playbook `secure-sdlc-rollout`, skills `cloud-security-basics`, `secrets-in-code`, `gdpr-engineering` ; agent `secure-architect-agent` ; cerveau `cost-of-attack`.

## Fonctionnement

Analyse approfondie : [HOW_IT_WORKS.md](../HOW_IT_WORKS.md). La version courte :

### :zap: Chargement des skills (divulgation progressive)
Au démarrage de la session, l'agent ne lit que le `name` et la `description` de chaque skill installée. Cela ne coûte presque aucun contexte. Quand votre prompt correspond à une description, l'agent charge le corps complet de la skill : le paragraphe de cadrage, le Quick Workflow numéroté, les procédures par phase avec commandes exactes, les cas limites, les chemins d'escalade, le point de vue du défenseur et les références clés. Une bonne `description` décide si une skill sera jamais utilisée, c'est pourquoi le scoreur de qualité note la densité des déclencheurs.

### :link: Composition et graphe de dépendances
Les skills se composent via trois types d'arêtes dans le frontmatter :

- `requires` : prérequis durs. `webapp-pentest-methodology` requiert `recon-active`, `web-sqli`, `web-xss` et `auth-attacks`. L'installateur résout toute la fermeture `requires` plus `extends` et installe toute la chaîne.
- `extends` : spécialisation. Une skill étend une plus large quand elle creuse l'une de ses phases.
- `relates` : liens "voir aussi". `web-sqli` est liée à `web-xss` et `api-security-testing`. Ils guident la découverte, pas l'installation.

Les sous-skills ajoutent une arête de plus : `parent`. Une sous-skill vit dans `skills/<domain>/<skill>/sub/<sub>/SKILL.md` et son champ `parent` doit nommer la skill parente qui l'englobe. Le validateur impose deux règles sur tout le graphe : chaque nom doit résoudre vers un artefact réel, et les arêtes `requires` plus `extends` plus `parent` ne doivent former aucun cycle. Un cycle ou une référence pendante fait échouer la CI.

### :busts_in_silhouette: Les agents lient skills, cerveaux et mémoire
Chaque agent est un fichier `agents/<name>/AGENT.md` avec un contrat de frontmatter fixe : un rôle, les skills qu'il charge, les cerveaux avec lesquels il raisonne, un mode de mémoire (`stateless` ou `persistent`), un fichier d'escalade et des contraintes dures qu'il ne brise jamais. Les agents sont des rôles opérationnels que vous pouvez exécuter : `recon-agent` transforme des cibles inconnues en inventaire cadré, `pentest-reporter-agent` transforme des findings bruts en rapports auxquels les dirigeants font confiance.

### :brain: Les cerveaux sont des schémas de raisonnement réutilisables
Des cerveaux comme `attacker-mindset` (penser en graphes d'attaque, prendre le chemin le moins cher), `evidence-chain` (chaque affirmation remonte à une source) et `threat-modeling` (les actifs d'abord, frontières de confiance, énumération façon STRIDE) se branchent sur n'importe quel agent. Seize cerveaux couvrent le raisonnement offensif, le raisonnement défensif, le débogage, le commandement d'incident et la décision sous pression.

### :floppy_disk: La mémoire a un schéma, pas juste de l'intuition
La mémoire de l'agent suit [memory/MEMORY_SCHEMA.md](../memory/MEMORY_SCHEMA.md) : entrées épisodiques (événements horodatés, TTL de 30 jours), entrées sémantiques (faits durables) et entrées procédurales (comment les choses se font). [memory/LIFECYCLE.md](../memory/LIFECYCLE.md) définit capture, consolidation et expiration ; [memory/HYGIENE.md](../memory/HYGIENE.md) la garde propre. Le CLI [memory-store](../tools/memory-store/) est un petit magasin SQLite que les agents utilisent pour lire et écrire la mémoire.

### :scroll: Les décisions posent les garde-fous
Cinq documents de décision permanents dans [decisions/](../decisions/) : politique d'escalade, matrice de risque, portes go/no-go, modèle d'ADR et analyse coût-bénéfice. Les agents pointent vers ces fichiers dans leur frontmatter, donc "quand est-ce que je m'arrête pour demander à un humain" est une politique, pas de l'improvisation.

### :clipboard: Les playbooks mènent l'engagement
Un playbook lie agents, skills, cerveaux et décisions en un runbook ordonné avec phases, critères d'entrée et de sortie, rôles et passations, conditions d'arrêt et artefacts produits. Huit playbooks couvrent les assessments AD, les assessments d'applications web, les pentests externes, les sprints de bug bounty, les revues cloud, les journées de triage SOC, les épidémies de malware et les déploiements SDLC sécurisés.

### :white_check_mark: Les portes CI maintiennent la barre
`scripts/validate.py` exécute 14 contrôles sur chaque artefact : champs de frontmatter requis, nom correspondant au slug du dossier, descriptions denses en déclencheurs, versions semver, valeurs de cycle de vie valides, dates `last_verified` sensées, résolution des dépendances, acyclicité du graphe, titres de corps requis (Quick Workflow, Edge cases, Key references), arêtes `parent` des sous-skills, contrats des agents/cerveaux/playbooks, cohérence du manifeste et hygiène du contenu (pas de tirets em). `scripts/score.py` note ensuite la qualité de 0 à 100. Fusionner exige 70+. Tout ce qui est rouge fait échouer le build.

![Architecture d'AgentArsenal](../assets/architecture.svg)

![Écosystème d'AgentArsenal](../assets/ecosystem.svg)

## Démarrage rapide

```bash
git clone https://github.com/mizazhaider-ceh/AgentArsenal.git
cd AgentArsenal
./install.sh --list            # affiche les domaines avec le nombre de skills, puis quitte
./install.sh --dry-run         # affiche ce qui serait copié, ne change rien
./install.sh                   # copie les skills stables dans votre dossier de skills
```

Installations ciblées :

```bash
./install.sh --category web --dry-run        # aperçu d'un domaine
./install.sh --category web                  # installe tout le domaine web
./install.sh --version web-sqli@1.0.0        # épingle une skill à une version
./install.sh --platform opencode --all       # installe pour OpenCode (19 plateformes)
./install.sh --list-platforms                # affiche le tableau des plateformes
./install.sh --rollback                      # restaure la sauvegarde précédente
./install.sh --help                          # toutes les options
```

Référence complète des flags : [COMMANDS.md](../COMMANDS.md).

## Installation pour votre plateforme

Un standard `SKILL.md`, tous les agents majeurs. Le nom de la plateforme est la valeur pour `install.sh --platform`. Chemins complets, particularités par plateforme (comme les permissions par skill d'OpenCode) et le fichier de mémoire de chaque plateforme : [platforms/PLATFORM_SUPPORT.md](../platforms/PLATFORM_SUPPORT.md).

| Plateforme | Commande d'installation | Dossier des skills |
| --- | --- | --- |
| Claude Code | `./install.sh --platform claude-code --all` | `~/.claude/skills/` |
| OpenCode | `./install.sh --platform opencode --all` | `~/.config/opencode/skills/` |
| Codex CLI | `./install.sh --platform codex-cli --all` | `~/.agents/skills/` |
| Gemini CLI | `./install.sh --platform gemini-cli --all` | `~/.gemini/skills/` |
| Cursor | `./install.sh --platform cursor --all` | `~/.cursor/skills/` |
| GitHub Copilot | `./install.sh --platform github-copilot --all` | `~/.copilot/skills/` |
| Amp | `./install.sh --platform amp --all` | `~/.agents/skills/` |
| Goose | `./install.sh --platform goose --all` | `~/.agents/skills/` |
| Cline | `./install.sh --platform cline --all` | `~/.agents/skills/` |
| Roo Code | `./install.sh --platform roo-code --all` | `~/.agents/skills/` |
| Kilo Code | `./install.sh --platform kilo-code --all` | `~/.agents/skills/` |
| Zed | `./install.sh --platform zed --all` | `~/.agents/skills/` |
| Warp | `./install.sh --platform warp --all` | `~/.agents/skills/` |
| Windsurf | `./install.sh --platform windsurf --all` | `~/.agents/skills/` |
| Kiro | `./install.sh --platform kiro --all` | `~/.kiro/skills/` |
| Qwen Code | `./install.sh --platform qwen-code --all` | `~/.qwen/skills/` |
| Crush | `./install.sh --platform crush --all` | `~/.agents/skills/` |
| Continue | `./install.sh --platform continue --all` | `~/.agents/skills/` |
| Aider | `./install.sh --platform aider` affiche un extrait de pointeur | pas de support des skills (utilise `AGENTS.md`) |

:bulb: **Astuce :** exécutez d'abord chaque commande avec `--dry-run` pour prévisualiser exactement ce qui sera copié. L'installateur sauvegarde vos skills existantes avant d'y toucher.

## Référence des commandes

Référence complète avec exemples vérifiés : [COMMANDS.md](../COMMANDS.md). Résumé :

<details>
<summary><strong>Déplier le résumé des commandes</strong></summary>

### install.sh (l'installateur sélectif)

Copie les dossiers de skills choisis dans le dossier de skills d'une plateforme, en résolvant les chaînes `requires`/`extends` depuis `arsenal-manifest.json`. Sauvegarde la cible avant d'y toucher.

| Flag | Ce qu'il fait |
| --- | --- |
| `--all` | Installe chaque skill du manifeste |
| `--category <name>` | Installe un domaine (voir les noms avec `--list`) |
| `--version <skill@ver>` | Installe une skill à une version épinglée, échoue en cas d'écart |
| `--platform <name>` | Définit la cible comme le dossier de skills d'une plateforme |
| `--target <dir>` | Dossier d'installation personnalisé |
| `--list` | Affiche les domaines avec le nombre de skills, puis quitte |
| `--list-platforms` | Affiche le tableau des plateformes supportées, puis quitte |
| `--dry-run` | Affiche ce qui serait copié, ne change rien |
| `--rollback` | Restaure la sauvegarde la plus récente de la cible |
| `--help` | Toutes les options |

### scripts/

| Script | Ce qu'il fait |
| --- | --- |
| `scripts/validate.py` | Validateur CI à 14 contrôles sur chaque artefact, quitte non-zéro à tout échec |
| `scripts/score.py` | Scoreur de qualité de 0 à 100 par artefact (fusion exige 70+) |
| `scripts/bundle.py` | Empaquette les skills en archive portable hors ligne avec manifeste |
| `scripts/derive_manifest.py` | Régénère `arsenal-manifest.json` depuis l'arborescence du dépôt |
| `scripts/gen_readme_catalog.py` | Régénère le badge de comptage et le catalogue du README depuis le manifeste |
| `scripts/gen_marketplace.py` | Régénère `.claude-plugin/marketplace.json` |
| `scripts/generate_docs.py` | Construit le site de documentation navigable dans `docs/` |
| `scripts/new_skill.py` | Échafaude une nouvelle skill avec frontmatter valide et squelette de corps |
| `scripts/test_tools.py` | Harnais de test pour les 47 outils CLI |

### tools/ (47 CLIs en bibliothèque standard uniquement)

```bash
python3 tools/port-scanner/port-scanner.py scanme.example.com -p 1-1024
python3 tools/file-hasher/file-hasher.py document.pdf
python3 tools/subnet-calculator/subnet-calculator.py 192.168.1.0/24
```

Chaque outil accepte `--help`, quitte 0 en succès et 2 en erreurs d'usage. Tableau complet dans [Outils CLI](#outils-cli).

</details>
## Catalogue des skills

246 skills dans 28 domaines. Régénéré depuis `arsenal-manifest.json` avec `scripts/gen_readme_catalog.py`.

> **Note de traduction :** les descriptions de chaque skill restent en anglais car ce sont les textes déclencheurs originaux des fichiers `SKILL.md`, qui sont en anglais. Les résumés par domaine sont traduits.

<details>
<summary><strong>Déplier le catalogue complet : 246 skills</strong></summary>

### :key: ad (8 skills)

*Chemins d'attaque Active Directory, de l'énumération à la forge de tickets, pour des assessments internes autorisés.*

- `ad-enumeration`: mapping an authorized Active Directory environment during an internal assessment or assumed breach exercise. AD enumeration with kerbrute for Kerberos user discovery, ldapsearch for direct LDAP queries, NetExec modules for SMB, LDAP, and WinRM enumeration, and BloodHound with SharpHound for attack path analysis.
- `ad-trust-attacks`: assessing Active Directory trust relationships on an authorized engagement. Covers trust enumeration, SID history abuse, cross forest Kerberos attacks, and trust direction review.
- `asreproasting`: testing Active Directory for AS-REP roasting on an authorized engagement. Covers finding accounts with Kerberos preauthentication disabled, requesting crackable AS-REP responses with GetNPUsers.py from impacket 0.12.0 and Rubeus 2.x, and offline cracking of krbasrep5 hashes with hashcat 6.2.6 mode 18200 or John the Ripper 1.9.0-jumbo-1.
- `bloodhound-methodology`: mapping Active Directory attack paths on an authorized engagement.
- `dcsync`: pulling Active Directory credential material through directory replication on an authorized engagement.
- `golden-ticket`: forging Kerberos tickets on an authorized Active Directory engagement after recovering the krbtgt account hash.
- `gpo-abuse`: assessing Group Policy security on an authorized AD engagement. Covers GPO enumeration, dangerous settings review, GPO based privilege escalation paths, and delegation review.
- `kerberoasting`: testing Active Directory for Kerberoasting on an authorized engagement. Covers SPN enumeration, TGS ticket requests with GetUserSPNs.py and Rubeus, offline cracking of krb5tgs hashes with hashcat 6.2.6, and targeted Kerberoasting against accounts you can write SPNs to.

### :robot: ai-security (8 skills)

*Attaque et défense des systèmes LLM et agents IA : injection de prompts, red teaming, garde-fous, chaîne d'approvisionnement.*

- `agent-hijacking`: testing an AI agent that can call tools or take actions on an authorized engagement. Covers tool output poisoning, confused deputy attacks, excessive agency, and prompt driven abuse of email, calendar, code execution, and browser tools.
- `ai-incident-response`: responding to a suspected security incident involving an AI system: a hijacked agent, a poisoned model, leaked prompts, or abusive use of inference infrastructure.
- `ai-supply-chain`: reviewing the supply chain of an AI system on an authorized assessment: model weights, datasets, base images, and third party integrations. Covers model provenance checks, poisoned dataset detection, dependency review for ML pipelines, and signing of artifacts.
- `guardrail-bypass-testing`: testing whether an LLM application's safety guardrails can be bypassed on an authorized engagement. Covers refusal classifier evasion, encoding tricks, roleplay framing, low resource language pivots, and multi step decomposition of refused requests.
- `llm-red-teaming`: running a structured red team exercise against an LLM application with authorization. Covers scoping, attack categorization (jailbreak, data extraction, insecure output, excessive agency), systematic test matrices, and scoring findings by impact.
- `model-extraction`: assessing whether a machine learning model behind an API can be stolen or copied on an authorized engagement. Covers prediction API scraping, membership inference, model inversion, and functionality stealing through systematic querying.
- `prompt-injection`: testing an LLM powered application for prompt injection on an authorized assessment. Covers direct and indirect injection, system prompt extraction, instruction override, delimiter smuggling, and multi-turn manipulation against chatbots, copilots, and agents.
- `rag-security`: assessing a retrieval augmented generation system on an authorized engagement. Covers document poisoning, embedding inversion, retrieval manipulation, context window stuffing, and access control gaps between the retriever and the user.

### :electric_plug: api (3 skills)

*Test et revue d'APIs : tests de sécurité, gRPC, revue OpenAPI, abus des limites de débit.*

- `api-security-testing`: testing REST, GraphQL, or internal APIs on an authorized engagement.
- `grpc-security`: assessing gRPC services on an authorized engagement. Covers service enumeration via reflection, auth review, message validation, and intercepting gRPC traffic.
- `openapi-security-review`: reviewing an OpenAPI specification for security issues on an authorized engagement. Covers contract vs implementation drift, auth scheme review, schema validation gaps, and finding hidden endpoints.

### :lock: auth (4 skills)

*Casser et réparer l'authentification : attaques de credentials, gestion des sessions, WebAuthn.*

- `auth-attacks`: testing authentication on an authorized engagement.
- `password-attacks`: cracking password hashes or auditing password strength on an authorized engagement. Covers hash identification, hashcat 6.2.6 and John the Ripper 1.9.0-jumbo-1 workflows, wordlist strategy, rule-based mutation, mask and hybrid attacks, and interpreting results for the report.
- `session-management-security`: assessing session management on an authorized web engagement. Covers cookie attributes, session fixation, timeout and rotation, concurrent session handling, and logout completeness.
- `webauthn-security`: assessing or implementing WebAuthn and passkeys on an authorized engagement. Covers registration and authentication ceremonies, attestation review, common implementation flaws, and fallback security.

### :car: automotive (8 skills)

*Sécurité des véhicules : bus CAN, ECUs, entrée sans clé, ISO 21434, V2X.*

- `automotive-ethernet`: assessing automotive Ethernet on a vehicle or bench setup you own or have authorization to test. Covers BroadR-Reach and 100BASE-T1 basics, SOME/IP service discovery, DoIP diagnostics, and VLAN segmentation in zonal architectures.
- `automotive-threat-model`: building a threat model for a vehicle or automotive component on an authorized engagement. Covers asset and attacker profiling, attack surface mapping across interfaces, attack trees for key scenarios, and prioritizing testing from the model.
- `can-bus-security`: assessing CAN bus security on a vehicle or bench setup you own or have authorization to test. Covers CAN sniffing with SocketCAN, message reverse engineering, injection testing, and gateway segmentation review.
- `ecu-firmware`: analyzing ECU firmware on an authorized assessment or your own bench hardware. Covers firmware extraction from ECUs, update package analysis, UDS flashing flows, and static review of automotive code.
- `iso21434-basics`: you need working knowledge of ISO/SAE 21434 for automotive cybersecurity work. Covers the standard's structure, TARA (threat analysis and risk assessment), cybersecurity planning, and how assessments map to its clauses.
- `keyless-entry-attacks`: assessing keyless entry and immobilizer systems on vehicles you own or have authorization to test, in a lab setting. Covers relay attack concepts, rolling code analysis, and defensive review of key fob protocols.
- `telematics-security`: assessing a telematics unit or connected car backend on an authorized engagement. Covers TCU architecture, cellular attack surface, backend API review, and remote command flows.
- `v2x-security`: assessing vehicle to everything communication on an authorized engagement or lab setup. Covers DSRC and C-V2X basics, message types (BSM, CAM, DENM), PKI and certificate review, and misbehavior detection concepts.

### :nut_and_bolt: binary (11 skills)

*Rétro-ingénierie et exploitation : bases du pwn, ROP, heap, shellcode, Ghidra, angr.*

- `angr-basics`: you need symbolic execution to explore program paths automatically, typically for CTF binaries, crackmes, or vulnerability research on code you are authorized to analyze.
- `binary-patching`: patching binaries in a lab on authorized targets: your own software, CTF binaries, or client approved test builds. Covers byte patching, assembly level fixes, and verifying patches.
- `firmware-analysis`: analyzing a firmware image from a device you own or are authorized to test. Covers Binwalk scanning and extraction, entropy analysis, SquashFS and archive recovery, bootloader and kernel identification, hunting hardcoded credentials and keys, and reverse engineering extracted binaries with Ghidra.
- `format-strings`: you need to exploit a format string vulnerability on an authorized target, such as a CTF pwn challenge or lab binary that passes user input directly to printf or a similar function.
- `ghidra-basics`: you need to reverse engineer a compiled binary on an authorized task, such as a CTF reversing challenge, malware triage in a lab, or auditing a binary you have permission to analyze.
- `heap-exploitation`: you need to exploit a heap memory bug on an authorized target, such as a CTF pwn challenge with use-after-free, heap overflow, or double free, or a lab binary using malloc and free unsafely.
- `kernel-exploit-basics`: learning kernel exploitation fundamentals in a lab with your own vulnerable VMs. Covers kernel attack surface, common bug classes, SMEP/SMAP/KASLR bypass concepts, and safe lab practices.
- `pwn-fundamentals`: you need to exploit a classic stack buffer overflow on an authorized target, such as a CTF pwn challenge or a lab binary you have permission to test.
- `rop-chains`: you need to build a Return Oriented Programming chain on an authorized target, such as a CTF pwn challenge with NX enabled and no easy win function.
- `shellcode-basics`: you need to write or use position-independent machine code payloads on an authorized target, such as a CTF pwn challenge where NX is disabled, a buffer you can execute, or a ROP chain that made memory writable and executable.
- `srop-attacks`: learning Sigreturn Oriented Programming in a lab on CTF style binaries you own. Covers sigreturn mechanics, frame forging, and chaining syscalls without gadgets.

### :link: blockchain (8 skills)

*Audits de smart contracts, menaces DeFi, attaques de bridges, portefeuilles, forensique on-chain.*

- `blockchain-forensics`: tracing cryptocurrency in an investigation on an authorized case. Covers address clustering, transaction graph analysis, exchange attribution, and following funds through mixers and bridges at the methodology level.
- `bridge-attacks`: assessing cross chain bridge security on an authorized engagement. Covers bridge architectures, validator and relayer trust models, message verification flaws, and the classic bridge hack patterns.
- `consensus-attacks`: you need working knowledge of consensus layer attacks for blockchain security assessments. Covers 51 percent attacks, selfish mining, long range attacks on PoS, eclipse attacks, and finality concepts.
- `dao-governance-risks`: assessing DAO governance security on an authorized engagement. Covers vote buying, flash loan governance attacks, proposal thresholds, timelock review, and multisig versus token vote tradeoffs.
- `defi-threats`: assessing DeFi protocols for economic and technical attacks on an authorized engagement. Covers flash loan attacks, oracle manipulation, sandwich attacks, and governance takeovers at the design level.
- `nft-fraud`: assessing NFT projects, marketplaces, or fraud patterns on an authorized engagement. Covers wash trading detection, metadata and minting flaws, phishing against collectors, and marketplace logic review.
- `smart-contract-audit`: auditing Solidity smart contracts on an authorized engagement or for your own project. Covers static analysis with Slither, manual review of access control and arithmetic, reentrancy testing, and upgradeability review.
- `wallet-security`: reviewing cryptocurrency wallet security for users or on an authorized product assessment. Covers seed phrase handling, hardware versus software wallets, transaction signing risks, and common theft techniques to defend against.

### :moneybag: bugbounty (1 skills)

*Mener un workflow de bug bounty de bout en bout, de la reco au rapport payé.*

- `bug-bounty-workflow`: hunting on a bug bounty program and you need a repeatable, professional methodology from scope to payout.

### :satellite: c2 (1 skills)

*Fondamentaux du commandement et contrôle pour des opérations red team autorisées.*

- `c2-fundamentals`: designing the command and control layer of an authorized red team or adversary emulation exercise.

### :cloud: cloud (16 skills)

*Surface d'attaque cloud : énumération AWS, Azure, GCP, escalade de privilèges IAM, conteneurs, Kubernetes, serverless.*

- `aws-enumeration`: enumerating an AWS environment during an authorized cloud assessment, bug bounty engagement, or lab exercise.
- `azure-enumeration`: enumerating a Microsoft Azure tenant or subscription during an authorized cloud assessment, bug bounty engagement, or lab exercise.
- `ci-secrets-management`: reviewing how CI/CD pipelines handle secrets on an authorized assessment. Covers secret storage in pipeline config, log leakage, pull request exposure, and OIDC versus long lived tokens.
- `cloud-cost-attack-surface`: assessing cloud cost as an attack surface on an authorized engagement. Covers denial of wallet, resource exhaustion billing, free tier abuse, and cost anomaly detection.
- `cloud-forensics`: doing forensics in cloud environments on an authorized investigation. Covers log sources per provider, snapshot and disk acquisition, volatile evidence in ephemeral workloads, and timeline building from cloud audit trails.
- `cloud-security-basics`: reviewing cloud security posture at concept level across AWS, GCP, and Azure, when checking IAM for least privilege and wildcard grants, when hunting public storage buckets and open security groups.
- `container-escape`: testing container escape during an authorized security assessment, CTF, or lab exercise.
- `container-image-security`: assessing container image security on an authorized engagement or in your own pipeline. Covers image scanning, base image choice, secret leakage in layers, and signing with Cosign.
- `gcp-enumeration`: enumerating a Google Cloud project, folder, or organization during an authorized cloud assessment, bug bounty engagement, or lab exercise.
- `iam-privesc`: assessing AWS IAM privilege escalation paths during an authorized cloud assessment, bug bounty engagement, or lab exercise.
- `k8s-pentest`: penetration testing Kubernetes clusters on an authorized engagement. Covers cluster enumeration, RBAC abuse, pod escape to node, etcd access, and service account token theft.
- `kubernetes-rbac`: enumerating and testing Kubernetes RBAC during an authorized cloud or cluster assessment, bug bounty engagement, or lab exercise.
- `multi-cloud-iam`: reviewing identity across multiple cloud providers on an authorized engagement. Covers federated identity design, cross cloud role assumptions, consistent least privilege, and finding the weakest provider.
- `s3-misconfigurations`: testing Amazon S3 buckets for misconfigurations during an authorized cloud assessment, bug bounty engagement, or lab exercise.
- `saas-security-review`: reviewing the security of a SaaS application your organization uses or builds. Covers SSO and SCIM, data residency, tenant isolation, admin controls, and offboarding.
- `serverless-security`: assessing serverless applications (Lambda, Cloud Functions, Azure Functions) on an authorized engagement. Covers function enumeration, event injection, IAM role abuse, and insecure dependencies.

### :closed_lock_with_key: crypto (9 skills)

*Attaques de cryptographie appliquée : RSA, oracles de padding, cassage de hashes, analyse TLS.*

- `crypto-fundamentals`: you face hashes, tokens, or ciphertext on an authorized test, CTF, or code review and need an operator-grade crypto workflow.
- `ecc-crypto-attacks`: assessing elliptic curve cryptography on an authorized engagement. Covers weak curve parameters, invalid curve attacks, nonce reuse in ECDSA, and implementation review.
- `hash-cracking`: you need to recover plaintexts from password hashes on an authorized engagement, such as cracking NTLM hashes from a domain dump, testing password strength after extracting hashes in scope, or solving CTF crypto challenges.
- `hash-length-extension`: testing for hash length extension attacks on an authorized assessment. Covers Merkle Damgard hashes, forging authenticated payloads with hashpump style extension, and reviewing MAC constructions.
- `padding-oracle`: you encounter CBC-mode ciphertext with distinguishable padding errors on an authorized test, CTF, or code review, and need to decrypt or forge messages without the key.
- `post-quantum-basics`: you need working knowledge of post quantum cryptography for planning and assessment. Covers the threat model, NIST standardized algorithms, hybrid deployments, and migration planning.
- `rng-attacks`: assessing random number generation on an authorized engagement. Covers weak PRNGs, seed prediction, VM snapshot issues, and reviewing randomness sources in code. Also use when tokens, keys, or nonces look predictable.
- `rsa-attacks`: you face an RSA challenge or misconfigured RSA on an authorized test, CTF, or code review and need an operator workflow for the classic attacks.
- `tls-analysis`: assessing the TLS configuration of a service you own or are authorized to test, or when decrypting your own captured traffic for troubleshooting. Covers certificate chain validation with openssl, protocol and cipher enumeration, testssl.sh comprehensive scans, TLS keylog decryption in Wireshark, and JA3/JA4 fingerprinting for detection.

### :shield: defensive (7 skills)

*Artisanat blue team : bases EDR, baselines de durcissement, défense anti-phishing, réponse aux ransomwares.*

- `backup-security`: designing or auditing backup security. Covers the 3-2-1 rule, immutability against ransomware, encryption, and restore testing. Also use when ransomware readiness needs the recovery side verified, not just assumed.
- `edr-basics`: deploying, operating, or triaging with Endpoint Detection and Response tooling on systems you are authorized to defend.
- `endpoint-hardening-baseline`: building or auditing endpoint hardening baselines for Windows, macOS, or Linux fleets. Covers CIS benchmark adaptation, practical control selection, compliance checking, and exception handling.
- `incident-playbooks`: preparing for or running a security incident as a defender: writing and maintaining incident response playbooks, defining severity levels and SLAs, assigning roles, running communications, executing scenario playbooks for malware, business email compromise, data theft, and denial of service, and running tabletop exercises.
- `phishing-defense`: defending an organization against phishing: hardening email authentication with SPF, DKIM, and DMARC, writing gateway and mailbox detection rules, triaging user-reported phish, analyzing headers URLs and attachments safely, running takedowns of phishing sites, and measuring resilience with simulations.
- `ransomware-response`: preparing for or responding to a ransomware incident as a defender. Covers pre-incident readiness (backups, segmentation, EDR), identifying the ransomware family, containment of encryption and lateral spread, evidence preservation, eradication, recovery from backups, decryptor checks, ransom decision factors, and post-incident hardening.
- `security-awareness-program`: building or improving a security awareness program. Covers phishing simulations, role based training, metrics that matter, and building a reporting culture.

### :wrench: engineering (41 skills)

*Artisanat du génie logiciel : git, CI/CD, Docker, Kubernetes, code sécurisé, débogage, performance.*

- `accessibility-security`: reviewing the intersection of accessibility and security in web applications. Covers how assistive tech interacts with security controls, CAPTCHA alternatives, and avoiding accessibility versus security tradeoffs.
- `ansible-basics`: automating server configuration with Ansible on an authorized engineering task. Covers inventory files, ad-hoc commands, playbook structure with plays tasks and handlers, idempotent modules, variables and vault-encrypted secrets, roles for reuse, and check mode plus diff for safe runs.
- `api-versioning`: designing or reviewing API versioning strategy. Covers URL vs header versioning, breaking change policy, deprecation process, and contract testing.
- `bash-advanced`: writing production-grade Bash 5.2 scripts: strict mode (set -euo pipefail), safe quoting and word splitting, arrays and associative arrays, parameter expansion, traps and cleanup handlers, getopts argument parsing.
- `chaos-engineering`: running chaos experiments to prove resilience. Covers hypothesis driven experiments, blast radius control, steady state metrics, and game days. Also use when "highly available" is claimed but never tested under failure.
- `cicd-security`: securing a CI/CD pipeline on an authorized engineering task.
- `code-reviewer`: reviewing code or pull requests for correctness, security, and maintainability, when auditing a codebase for vulnerabilities such as injection, broken authentication, insecure cryptography, and leaked secrets.
- `database-migrations`: designing or reviewing database migration practices. Covers migration authoring, zero downtime patterns, rollback strategy, and migration security review.
- `debugging-methodology`: diagnosing a bug or failure systematically: building a reproduction case, bisecting with git bisect, reading logs and stack traces, tracing syscalls with strace, debugging with gdb 15 or pdb, analyzing core dumps, forming and testing hypotheses one variable at a time, or writing a postmortem after an incident.
- `devsecops-pipeline`: designing or improving a DevSecOps delivery pipeline on an authorized engineering task. Covers pipeline stage design (build, test, scan, sign, deploy), placing SAST DAST and SCA gates, environment promotion with approvals, artifact promotion instead of rebuilds, SBOM generation, deployment strategies, and pipeline observability.
- `docker-deep`: building, hardening, or debugging Docker containers on an authorized engineering task. Covers multi-stage Dockerfiles, layer caching, minimal base images, non-root users, Compose for multi-service stacks, volumes and networks, image scanning, resource limits, and troubleshooting with logs, exec, and inspect.
- `feature-flags`: implementing or reviewing feature flags. Covers flag lifecycle, targeting rules, kill switches, and flag hygiene. Also use when a release needs gradual rollout or instant rollback without a redeploy.
- `git-workflows`: choosing a branching model for a team, when writing clean atomic commits, when rebasing a feature branch or resolving rebase conflicts, when running a disciplined pull request review.
- `github-actions`: writing or debugging GitHub Actions workflows on an authorized engineering task. Covers workflow triggers, jobs and steps, matrix builds, caching dependencies, artifacts, reusable workflows, pinning third-party actions by SHA, OIDC authentication to clouds, and local testing with act 0.2.71.
- `gitops-workflows`: implementing or reviewing GitOps for Kubernetes deployments. Covers repo structure, Argo CD or Flux setup, promotion between environments, secret handling, and drift detection.
- `go-basics`: writing, building, or reviewing Go programs on an authorized engineering task. Covers module setup with go mod, building and cross-compiling, gofmt and go vet hygiene, unit testing with the testing package, error handling idioms, goroutines and channels for concurrency, the race detector, and static binaries for deployment.
- `jq-mastery`: processing JSON on the command line with jq 1.7.1: selecting and filtering fields, transforming API responses, building JSON objects, aggregating with map/select/reduce, converting JSON to CSV or TSV, handling raw text input with slurp mode, parsing logs that contain JSON, or debugging why a filter returns null.
- `kubernetes-basics`: deploying or troubleshooting workloads on Kubernetes on an authorized engineering task. Covers kubectl 1.31 context and namespace handling, Pods, Deployments, Services, ConfigMaps and Secrets, resource requests and limits, liveness and readiness probes, rolling updates and rollbacks, logs and port-forward debugging, and basic RBAC.
- `load-testing`: load testing a system you own or are authorized to test. Covers test design, ramp profiles, bottleneck analysis, and interpreting results.
- `make-basics`: writing or fixing Makefiles with GNU Make 4.4: understanding targets, prerequisites, and recipes, using automatic variables ($@, $<, $^), writing pattern rules, declaring .PHONY targets.
- `nginx-hardening`: hardening an nginx 1.27 web server or reverse proxy: writing secure server blocks, disabling version banners, configuring modern TLS, adding security headers (HSTS, CSP, X-Frame-Options), rate limiting with limit_req.
- `performance-tuning`: making a system faster on purpose: establishing a baseline benchmark with hyperfine 1.18, profiling Python with cProfile, finding CPU, memory, disk, or network bottlenecks on Linux, tuning database queries and caches.
- `postgresql-tuning`: diagnosing or improving PostgreSQL performance on an authorized engineering task. Covers EXPLAIN ANALYZE reading, index design and bloat checks, pg_stat_statements for slow query hunting, autovacuum tuning, connection pooling, key postgresql.conf settings, and backup verification.
- `prometheus-monitoring`: setting up or debugging Prometheus monitoring on an authorized engineering task. Covers Prometheus 3.1 server config and targets, PromQL queries for RED and USE metrics, recording rules, Alertmanager 0.28 routing and silences, node_exporter 1.8 host metrics, Grafana 11.5 dashboards, and alert runbook practices.
- `python-advanced`: writing or reviewing advanced Python code on an authorized engineering task.
- `python-cli-tooling`: building command-line tools in Python using only the standard library, when designing an argparse interface with subcommands, when adding --help, --version, --sample, and --output json conventions to a script.
- `redis-basics`: operating Redis 7.4 in development or production: installing and configuring a server, choosing data types (strings, hashes, lists, sets, sorted sets, streams), writing and reading keys with redis-cli, setting TTLs.
- `regex-mastery`: writing or debugging regular expressions: choosing between BRE, ERE, and PCRE flavors, crafting grep, sed, and awk patterns, using character classes, anchors, quantifiers, groups, backreferences, and lookarounds.
- `rest-api-design`: designing a REST API from scratch or reviewing an existing one: naming resources and URIs, choosing HTTP methods and status codes correctly, versioning the API, designing pagination, filtering, and sorting.
- `rust-basics`: writing, building, or reviewing Rust programs on an authorized engineering task.
- `secrets-in-code`: finding and removing secrets from source code on an authorized codebase. Covers scanner setup, historical cleanup, rotation after exposure, and preventing recurrence with pre commit hooks.
- `secure-coding`: writing or fixing code that handles untrusted input, when choosing safe APIs for SQL, shell, and file access, when implementing password hashing, session tokens, and output encoding.
- `sqlite-deep`: working with SQLite databases on an authorized engineering task. Covers the sqlite3 CLI, schema design, index strategy, WAL mode and pragmas for performance and durability, parameterized queries, online backup API, integrity checks, and debugging locked databases.
- `ssh-hardening`: hardening OpenSSH 9.8 servers and clients: writing a secure sshd_config (key-only auth, no root login, modern ciphers and key exchange), auditing the effective config with sshd -T, managing host keys.
- `systemd-deep`: working deeply with systemd 256 on Linux: writing and debugging service, timer, socket, and target units, using systemctl and journalctl effectively, replacing cron jobs with systemd timers.
- `technical-writing`: writing documentation people actually read: planning a doc for its audience, structuring tutorials, how-to guides, reference, and explanations (Diataxis), writing clear plain-English procedures with verifiable steps.
- `terraform-basics`: writing or operating Terraform infrastructure as code on an authorized engineering task. Covers init plan apply workflow, HCL resource and variable syntax, outputs, state management and locking, remote backends, modules, workspaces, fmt and validate checks, and safe destroy procedures.
- `testing-strategies`: building a test strategy for a Python project: choosing what to test at each level of the test pyramid, writing pytest unit tests with fixtures and parametrize, mocking external services, measuring coverage, writing integration and end-to-end tests, fixing flaky tests, running tests in CI, or reviewing whether a codebase is under-tested.
- `tmux-workflows`: working with tmux 3.4 for persistent terminal sessions: creating and managing sessions, windows, and panes, customizing key bindings and the status bar in tmux.conf, using copy mode to search and copy scrollback.
- `typescript-basics`: writing, building, or reviewing TypeScript on an authorized engineering task. Covers strict tsconfig setup, type and interface modeling, unions and narrowing, generics, async and await patterns, DOM-free Node.js scripting, npm scripts, ESLint checks, and compiling to clean JavaScript.
- `vim-mastery`: editing text at speed with Vim 9.1: learning motions, operators, and text objects, combining them into composable editing commands, managing buffers, windows, and tabs, recording and replaying macros.

### :mag: forensics (7 skills)

*Informatique forensique : forensique disque, mémoire, navigateur, e-mail, mobile et logs.*

- `browser-forensics`: analyzing browser artifacts in an authorized investigation. Covers history, cookies, cache, downloads, and session artifacts for Chrome, Firefox, Edge, and Safari. Also use when web activity is the key timeline source.
- `disk-forensics`: examining a disk image or forensic copy of a drive during an investigation. Covers The Sleuth Kit and Autopsy workflows: partition layout, file carving, deleted file recovery, timeline generation, hash analysis, and keyword search.
- `email-forensics`: investigating a suspicious email during phishing triage or incident response. Covers full header analysis, Received chain tracing, SPF/DKIM/DMARC verification with dig, attachment extraction and hashing, URL and indicator extraction, and telling spoofing from compromise.
- `forensics-fundamentals`: you must investigate a disk image, memory dump, or compromised host under proper legal authority, on an authorized incident response engagement, lab, or CTF.
- `log-forensics`: reconstructing an incident from system and application logs you are authorized to analyze. Covers Linux journald and syslog, JSON log filtering with jq, Windows EVTX triage, authentication log hunting for brute force and lateral movement, detecting log tampering and gaps, and building a cross-source timeline.
- `memory-forensics`: analyzing a RAM dump or live memory image during incident response or a forensic investigation.
- `mobile-forensics`: doing forensics on mobile devices in an authorized investigation. Covers acquisition methods, iOS and Android artifacts, app data analysis, and handling encryption.

### :computer: hardware (8 skills)

*Piratage matériel : UART et JTAG, glitching, canaux auxiliaires, extraction de firmware.*

- `emi-emc-basics`: you need working knowledge of electromagnetic interference and compatibility for security hardware work. Covers how emissions leak information, how to reduce a device's emission profile in the lab, and what EMC concepts matter when probing or shielding a target you own.
- `firmware-extraction`: you need to get firmware off a device or out of an update file on an authorized assessment. Covers update package unpacking, SPI flash reading with flashrom, binwalk carving, and filesystem extraction from images you own or have permission to test.
- `glitching-attacks`: assessing fault injection resistance of a device you own or have authorization to test. Covers voltage glitching concepts, clock glitching concepts, fault models, and reviewing firmware for missing fault checks.
- `hardware-reversing`: reverse engineering an embedded device you own or have authorization to test. Covers board teardown and documentation, firmware analysis workflow, protocol sniffing between chips, and building a full picture from hardware plus software.
- `pcb-analysis`: analyzing a printed circuit board on an authorized hardware assessment or in your own lab. Covers visual inspection, component identification, power rail mapping, signal tracing with a multimeter, and spotting hardware implants or tampering.
- `secure-boot-bypass`: assessing secure boot implementations on devices you own or have authorization to test. Covers boot chain mapping, signature verification review, rollback protection checks, and common bypass classes at the design level.
- `side-channels`: assessing a device for side channel leakage on an authorized hardware engagement or in your own lab. Covers power analysis basics, timing attack measurement, electromagnetic probing concepts, and simple countermeasure review.
- `uart-jtag`: working with embedded hardware on an authorized assessment or lab device you own. Covers finding UART consoles with a logic analyzer, getting a root shell over serial, identifying JTAG and SWD headers, and dumping memory with OpenOCD.

### :factory: ics-scada (8 skills)

*Systèmes de contrôle industriels : Modbus, DNP3, PLCs, segmentation des réseaux SCADA.*

- `dnp3-basics`: you need working knowledge of DNP3 for an OT assessment or lab. Covers DNP3 architecture (master and outstation), addressing, function codes, Secure Authentication basics, and where DNP3 appears in electric utility and water networks.
- `historian-security`: assessing a process historian on an authorized OT engagement. Covers historian architecture, the IT to OT data path, access control on trend and alarm data, and injection of false data.
- `ics-incident-response`: responding to a suspected incident in an OT or SCADA environment. Covers safety first triage, OT evidence collection without disrupting processes, working with operations, and recovery that respects physical constraints.
- `modbus-security`: assessing Modbus TCP or Modbus RTU on an authorized OT engagement or lab. Covers device discovery, function code enumeration, register mapping, detecting unsafe writes, and reviewing Modbus exposure.
- `opc-ua-security`: assessing OPC UA servers on an authorized OT engagement or lab. Covers endpoint discovery, security policy review, certificate handling, anonymous access checks, and node enumeration.
- `plc-basics`: you need working knowledge of programmable logic controllers for an OT assessment or lab. Covers PLC architecture, scan cycle, ladder logic reading, common vendors and protocols, and how PLCs fit into the Purdue model.
- `safety-systems`: you need to understand safety instrumented systems for OT security work. Covers what SIS does, why it is separate from process control, the security boundaries around it, and how to assess without ever endangering people.
- `scada-network-seg`: designing or assessing network segmentation for OT and SCADA environments on an authorized engagement. Covers the Purdue model, conduit and zone design per IEC 62443, firewall rule review between IT and OT, and validating that segmentation actually holds.

### :rotating_light: incident (3 skills)

*Réponse aux incidents : le processus IR, exercices sur table, communications de crise.*

- `crisis-communications`: planning or executing communications during a security incident. Covers holding statements, stakeholder mapping, notification timelines, and working with legal and PR.
- `incident-response`: a security incident is suspected or confirmed and you need a disciplined response on authorized systems. Covers the NIST 800-61 lifecycle: preparation, detection and analysis, containment, eradication, recovery, and lessons learned.
- `tabletop-exercises`: planning and running incident response tabletop exercises. Covers scenario design, facilitation, injects, and turning findings into playbook fixes. Also use when the IR plan exists on paper but has never been tested.

### :penguin: linux (3 skills)

*Sécurité Linux : durcissement, sécurité eBPF, durcissement des conteneurs.*

- `ebpf-security`: assessing eBPF usage on Linux systems you own or are authorized to review. Covers eBPF program inventory, capability review, malicious eBPF detection, and safe development practices.
- `linux-container-hardening`: hardening Linux containers you run. Covers runtime options, seccomp and AppArmor profiles, capability drops, read only filesystems, and user namespaces. Also use when a container deployment needs a security baseline.
- `linux-hardening`: hardening a Linux server for production, when locking down SSH with key-only authentication, when writing a default-deny firewall with ufw or nftables, when disabling unneeded services.

### :bug: malware (4 skills)

*Analyse de malware : triage statique, sandbox dynamique, packers, règles YARA.*

- `dynamic-sandbox`: a suspicious file needs to be executed to reveal its behavior, and only inside an isolated sandbox or disposable VM with no route to production networks.
- `packer-analysis`: static triage finds a packed or encrypted executable and you need the real payload underneath. Covers packer identification with Detect It Easy, the trivial UPX case, entropy and section analysis to map the packed regions, manual unpacking concepts using memory dumps, overlay data handling, and re-triaging the unpacked binary.
- `static-triage`: you receive a suspicious file and must decide what it is without executing it. Covers the full static triage pipeline in an isolated lab: hashing and file identification, strings and entropy analysis, import and section inspection, YARA scanning, packer detection, and headless Ghidra function listing.
- `yara-rules`: you need to write, test, or tune YARA rules for malware detection and hunting. Covers rule anatomy, string types and modifiers, condition logic, the pe/elf/math/hash/dotnet modules, testing against clean and malicious corpora, measuring false positives, atom quality for performance, and YARA-X differences.

### :floppy_disk: memory (5 skills)

*Skills de mémoire d'agents : capture, rappel, consolidation, hygiène et état.*

- `agent-state`: an agent needs to save where it is in a long task so it can resume later, or when handing a task to another agent without losing context. Covers checkpointing progress as episodic entries, restoring state with targeted recall, writing handover notes that another agent can act on, and cleaning up stale checkpoints when the task finishes.
- `memory-capture`: an agent needs to record what it learned so future runs can reuse it, or when an operator wants durable notes from a task that took real effort.
- `memory-consolidation`: duplicate or overlapping memory entries pile up, or when repeated episodic observations should become one durable semantic fact. Covers dry-run review of merge candidates, merging near-duplicates safely, promoting episodic observations to semantic knowledge with raised confidence, and resolving which entry survives a merge.
- `memory-hygiene`: the memory store needs a health check: removing duplicates safely, resolving contradictory entries, decaying stale confidence, redacting secrets that slipped in, keeping an audit trail, or enforcing size budgets.
- `memory-recall`: an agent needs to look up what it already knows before doing new work, or when an operator wants the facts behind a past decision. Covers query patterns (keyword choice, kind filters, tag and agent filters), how the memory-store relevance ranking works, interpreting confidence and staleness, and recalling procedural knowledge mid-task.

### :iphone: mobile (5 skills)

*Sécurité mobile : analyse statique et dynamique Android, bases iOS, durcissement.*

- `android-dynamic`: you need to test a running Android app on an authorized engagement, such as a client mobile app pentest or a CTF APK that only reveals behavior at runtime.
- `android-hardening`: hardening Android apps you build or review. Covers network security config, root and tamper detection, secure storage, and anti reverse engineering appropriate to the risk.
- `android-static`: you need to reverse engineer an Android APK you are authorized to test, such as a client mobile application on a penetration test or a CTF challenge APK.
- `ios-basics`: you need to assess an iOS application you are authorized to test, such as a client iPhone app on a penetration test or a CTF challenge IPA.
- `ios-dynamic-analysis`: dynamically analyzing iOS apps on an authorized engagement with a test device you own. Covers jailbreak lab setup, Frida instrumentation, traffic interception, and runtime data inspection.

### :globe_with_meridians: network (19 skills)

*Attaques et analyse réseau : Nmap, DNS, SMB, saut de VLAN, sans-fil, pivoting.*

- `arp-spoofing`: performing authorized man-in-the-middle testing on a local network segment.
- `bgp-security`: assessing BGP security on an authorized network engagement or lab. Covers route hijack concepts, RPKI validation review, BGP monitoring, and peer configuration audits.
- `bluetooth-le`: assessing Bluetooth Low Energy devices on authorized engagements, such as beacons, locks, wearables, or IoT sensors in scope.
- `dhcp-attacks`: assessing DHCP security on an authorized network or lab. Covers rogue DHCP servers, DHCP starvation, option injection, and DHCP snooping review.
- `dns-enumeration`: enumerating DNS on authorized engagements, internal or external. Covers forward and reverse lookups, record harvesting (A, MX, TXT, SRV, NS, SOA), zone transfer (AXFR) attempts, DNSSEC NSEC zone walking, subdomain brute forcing with curated wordlists, and wildcard detection with dig, host, dnsrecon, and nmap.
- `firewall-evasion`: nmap scans are blocked, filtered, or rate limited by firewalls and IDS on authorized engagements. Covers packet fragmentation, MTU games, decoy scans, source port spoofing, idle (zombie) scans, timing and delay tuning, bad checksums, data length padding, and tunneling scans through proxies.
- `ipv6-attacks`: testing IPv6 on authorized engagements, especially dual-stack networks where IPv6 is enabled but unmonitored.
- `ipv6-deep-dive`: assessing IPv6 on an authorized network engagement. Covers IPv6 discovery, extension header abuse, rogue router advertisements, and reviewing dual stack parity.
- `llmnr-poisoning`: capturing authentication hashes on authorized Windows LAN segments. Covers how LLMNR and NBT-NS name resolution can be poisoned, running Responder to answer victim queries, capturing NetNTLMv1 and NetNTLMv2 hashes, relaying safely within scope, cracking captured hashes with hashcat, and the Group Policy fixes that stop it.
- `netflow-analysis`: analyzing NetFlow, sFlow, or IPFIX data for security investigations or baselining. Covers flow collection review, beaconing detection, data exfiltration spotting, and building baselines.
- `network-pivoting`: an authorized engagement gives you a foothold host and you must reach deeper network segments through it. Pivoting with SSH local, remote, and dynamic port forwarding, proxychains routing for proxyless tools, chisel TCP and UDP tunnels, ligolo-ng tun interfaces for full layer 3 access, and socat relays.
- `nmap-methodology`: planning or running nmap scans during authorized engagements: host discovery options, TCP SYN, connect, UDP, NULL, FIN, Xmas, and ACK scan types, service and OS detection, timing templates T0 to T5.
- `sdwan-security`: assessing SD-WAN deployments on an authorized engagement. Covers overlay security, controller and orchestrator review, branch device hardening, and segmentation across the WAN.
- `smb-enumeration`: enumerating SMB services on authorized Windows or Samba targets. Covers finding SMB hosts, testing null sessions, reading share listings, checking SMB signing, enumerating users and groups with rpcclient and Impacket, riding RIDs to dump usernames, and searching shares for sensitive files with smbclient.
- `snmp`: enumerating SNMP services on authorized targets, typically UDP 161. Covers finding SNMP hosts, testing default and common community strings, walking MIB trees with snmpwalk and snmpbulkwalk for system info, interfaces, routes, users, and running processes, probing SNMP write access safely, and handling SNMPv3 auth.
- `stp-attacks`: assessing Spanning Tree Protocol on an authorized network or lab. Covers STP root takeover, BPDU guard review, and topology manipulation. Also use when reviewing switch hardening on enterprise or campus networks.
- `vlan-hopping`: testing VLAN segmentation on an authorized network assessment or lab. Covers switch spoofing, double tagging, DTP negotiation abuse, and validating that VLANs actually isolate.
- `wireless-wpa`: testing Wi-Fi security on authorized engagements with written permission covering the wireless network.
- `zero-trust-networking`: designing or assessing zero trust network architectures on an authorized engagement. Covers identity based access, microsegmentation review, policy engine assessment, and validating that implicit trust is actually gone.

### :eyes: osint (6 skills)

*Renseignement de sources ouvertes : domaines, pseudos, images, réseaux sociaux, threat intel.*

- `domain-osint`: investigating domains, DNS history, certificates, and hosting infrastructure from public sources on an authorized engagement. Covers RDAP and WHOIS lookups, DNS enumeration past and present, certificate transparency mining, passive DNS pivoting, ASN and BGP analysis, and infrastructure link analysis.
- `image-osint`: extracting intelligence from images on an authorized investigation. Covers metadata analysis, reverse image search, geolocation from visual clues, and authenticity checks.
- `osint-methodology`: planning and running an open source intelligence collection effort against public sources only. Covers the OSINT cycle, defining collection requirements, building a collection plan, source evaluation, operational security for researchers, sock puppet hygiene, documentation and evidence handling, and reporting.
- `social-media-osint`: researching publicly visible social media content on an authorized engagement. Covers profile analysis and attribution, timeline and network mapping, image and video metadata, geolocation from public posts, sock puppet OPSEC, and lawful limits.
- `threat-intel`: working with cyber threat intelligence on a defensive team: collecting IOCs, evaluating feeds, running a MISP instance, writing STIX/TAXII sharing packages, scoring and aging indicators, and turning intel into detections and blocks.
- `username-osint`: investigating a username across platforms on an authorized investigation. Covers username enumeration, profile correlation, timeline building, and operational security.

### :bust_in_silhouette: privacy (8 skills)

*Ingénierie de la confidentialité : RGPD, anonymisation, confidentialité différentielle, études d'impact.*

- `anonymization-techniques`: you need to anonymize a dataset for sharing or analysis. Covers k-anonymity, l-diversity, generalization and suppression, re identification risk assessment, and why naive masking fails.
- `consent-management`: implementing or auditing consent for data processing: cookie banners, app permissions, and marketing opt ins. Covers consent records, withdrawal handling, dark pattern avoidance, and verifying that backend processing respects the choice.
- `data-minimization`: reducing personal data collection and storage in a system you build or review. Covers purpose mapping, field level audits, replacing identifiers with pseudonyms, and safe defaults.
- `differential-privacy`: you need to publish statistics or train models on sensitive data without exposing individuals. Covers epsilon budgets, Laplace and Gaussian noise, composition, and the practical limits of the guarantee.
- `dsr-automation`: automating data subject requests: access, erasure, portability, and rectification at scale. Covers request intake and identity verification, orchestration across datastores, processor propagation, and SLA tracking.
- `gdpr-engineering`: building or reviewing systems for GDPR compliance from the engineering side. Covers data mapping, lawful basis in code, retention automation, and data subject rights implementation.
- `privacy-impact-assessment`: running a privacy impact assessment (DPIA) for a new feature or system. Covers when a DPIA is required, the assessment steps, risk scoring, mitigation planning, and getting sign off.
- `privacy-threat-model`: building a privacy threat model for a system you design or review. Covers LINDDUN methodology, attacker profiling for privacy, linkability and identifiability analysis, and turning the model into engineering requirements.

### :arrow_up: privesc (2 skills)

*Escalade de privilèges sous Linux et Windows, pas à pas.*

- `privesc-linux`: you hold a low-privilege Linux shell on an authorized engagement, lab, or CTF and need a reliable path to root.
- `privesc-windows`: you hold a low-privilege Windows shell on an authorized engagement, lab, or CTF and need a path to SYSTEM or Administrator.

### :telescope: recon (2 skills)

*Reconnaissance : découverte passive et active des cibles avant de toucher quoi que ce soit.*

- `recon-active`: you have written authorization and need to directly probe the target: DNS zone transfer attempts, authoritative NS interrogation, subdomain brute forcing, reverse DNS sweeps, ICMP and TCP host discovery, and initial service discovery with dig, nmap, masscan, gobuster, and ffuf.
- `recon-passive`: starting authorized reconnaissance on a target domain or organization while staying off the target's own infrastructure. Passive reconnaissance with whois, dig against public resolvers, crt.sh certificate transparency logs, Shodan, Censys, theHarvester, Sublist3r, and Amass in passive mode.

### :police_car: soc (14 skills)

*Opérations de sécurité : SIEM, règles Sigma, Suricata, threat hunting, timelines DFIR, purple team.*

- `dark-web-monitoring`: setting up monitoring for your organization's data on criminal forums and marketplaces. Covers collection strategy, credential leak monitoring, brand and executive exposure, and operational security for the monitoring itself.
- `detection-as-code`: building detections as versioned, tested code. Covers Sigma rule authoring, detection pipelines, unit testing detections, and CI for the SOC.
- `dfir-timeline`: building a forensic timeline for an authorized investigation. Covers evidence source collection, timestamp normalization, super timeline creation with Plaso, and analyzing the merged timeline for attacker activity.
- `edr-evasion-detection`: reviewing whether attacker techniques evade the deployed EDR on an authorized assessment. Covers common evasion classes, detection gap testing with atomic tests, and tuning recommendations.
- `honeypot-ops`: deploying and operating honeypots for detection and intelligence on your own network. Covers honeypot types, deployment safety, alert tuning, and turning captures into detections.
- `memory-malware-hunting`: hunting malware in memory images on an authorized investigation. Covers Volatility 3 workflows, process and injection detection, network artifact recovery, and finding fileless malware.
- `purple-team-exercises`: running purple team exercises that pair offense and defense on authorized systems. Covers exercise design, TTP selection, detection validation, and turning results into improved detections.
- `siem-detections`: building, tuning, or operating SIEM detections on an authorized blue team engagement or in a lab SOC. Covers log source inventory, normalization, writing Splunk SPL and Elastic detection rules, correlation and threshold logic, alert tuning to cut false positives, detection coverage mapping to MITRE ATT&CK, and measuring MTTD and MTTR.
- `sigma-rules`: writing, converting, or testing Sigma detection rules for a defensive detection program. Covers Sigma rule structure, logsource taxonomy, detection selection syntax, modifiers, conditions, testing with the Sigma CLI, and converting one rule to Splunk SPL, Elastic, and other backends.
- `suricata-ids`: deploying, tuning, or troubleshooting Suricata as a network intrusion detection sensor on a network you are authorized to monitor.
- `threat-actor-profiling`: building or reviewing threat actor profiles for intelligence or defense planning. Covers TTP mapping to MITRE ATT&CK, infrastructure patterns, victimology, and turning profiles into detection priorities.
- `threat-hunting`: proactively hunting for undetected intruders in an environment you are authorized to defend.
- `velociraptor-basics`: you need fast, targeted forensic collection across many endpoints during incident response or proactive hunting. Covers deploying the Velociraptor server, enrolling clients, running artifact collections from the GUI, writing basic VQL queries, launching hunts across the fleet, and using the offline collector for dead-box triage.
- `wazuh-basics`: deploying or operating Wazuh for host-based intrusion detection on infrastructure you are authorized to defend. Covers manager and agent architecture, agent enrollment, file integrity monitoring, security configuration assessment, custom rules and decoders, vulnerability detection, active response, and agent health monitoring.

### :spider_web: web (27 skills)

*Attaques d'applications web : SQLi, XSS, SSRF, SSTI, JWT, OAuth, GraphQL, plus la méthodologie complète de pentest.*

- `api-rate-limit-bypass`: testing API rate limits on an authorized assessment. Covers limit discovery, header and IP spoofing bypasses, endpoint and method variations, and distinguishing real enforcement from cosmetic headers.
- `cache-deception`: testing for web cache deception on an authorized assessment. Covers path confusion, cache key analysis, authenticated content caching, and proving cross user cache poisoning safely.
- `cache-poisoning`: testing web cache poisoning and web cache deception on an authorized engagement.
- `cors-misconfig`: testing cross-origin resource sharing (CORS) configuration on an authorized engagement.
- `csrf`: testing a web application for Cross-Site Request Forgery on an authorized engagement. Covers mapping state-changing requests, detecting missing or weak anti-CSRF tokens, building HTML proof-of-concept exploits, testing SameSite cookie behavior, bypassing Referer and Origin checks, and attacking login CSRF and token-validation flaws.
- `deserialization-attacks`: testing for insecure deserialization on an authorized assessment. Covers identifying serialization formats, Java, Python pickle, PHP, .NET, and Node.js vectors, plus safe proof of concept practices.
- `dom-clobbering`: testing for DOM clobbering on an authorized web assessment. Covers named element clobbering, clobbering to XSS escalation, and code patterns that are vulnerable.
- `file-upload-attacks`: testing file upload functionality on an authorized engagement.
- `graphql-security`: testing a GraphQL API on an authorized engagement. Covers finding the endpoint, abusing introspection for full schema dumps, enumerating queries and mutations, authorization testing on every field, batching attacks for brute force, nested query denial of service, IDOR through global IDs, and subscription abuse.
- `header-injection`: testing for HTTP header injection and response splitting on an authorized web assessment. Covers CRLF injection in reflected headers, cache poisoning via headers, log injection, and request smuggling adjacencies.
- `http-request-smuggling`: testing for HTTP request smuggling (desync) between a front-end proxy and a back-end server on an authorized engagement.
- `jwt-attacks`: testing JSON Web Token handling on an authorized engagement. Covers decoding and structure analysis, algorithm confusion (none algorithm, RS256 to HS256 key confusion), weak HMAC secret brute forcing, kid and jku/x5u header injection, claim tampering (sub, role, exp), and jwk injection.
- `lfi-rfi`: testing a web application for Local and Remote File Inclusion on an authorized engagement.
- `nosql-injection`: testing NoSQL-backed applications (MongoDB, CouchDB, Redis) for injection on an authorized engagement.
- `oauth-attacks`: testing OAuth 2.0 and OpenID Connect logins on an authorized engagement.
- `oauth2-deep-dive`: assessing OAuth 2.0 and OpenID Connect implementations on an authorized engagement. Covers flow selection, redirect URI validation, code and token theft, PKCE review, and common misconfigurations.
- `open-redirect`: testing for unvalidated redirects and forwards on an authorized engagement.
- `postmessage-security`: assessing postMessage communication between windows and iframes on an authorized engagement. Covers origin validation flaws, message handler review, and cross origin data leaks.
- `prototype-pollution`: testing JavaScript applications for prototype pollution on an authorized assessment. Covers detection via __proto__ payloads, gadget hunting, pollution to XSS escalation, and server side pollution in Node.js.
- `race-conditions`: testing for race conditions (time-of-check to time-of-use flaws) on an authorized engagement.
- `ssrf`: testing a web application for Server-Side Request Forgery on an authorized engagement.
- `ssti`: testing a web application for Server-Side Template Injection on an authorized engagement.
- `web-sqli`: testing a web application for SQL injection on an authorized engagement. Covers detection and confirmation probes, UNION-based extraction, boolean and time-based blind techniques, error-based extraction, second-order injection, and sqlmap 1.9.2 automation plus full manual fallback when automation is blocked.
- `web-xss`: testing a web application for cross-site scripting on an authorized engagement. Covers reflected, stored, and DOM-based XSS, context-aware payload crafting (HTML, attribute, JavaScript, and URL contexts), filter and WAF bypass techniques, and Content Security Policy analysis with safe proof-of-concept callbacks.
- `webapp-pentest-methodology`: planning or running a full web application penetration test on an authorized engagement.
- `websocket-security`: an application uses WebSockets (ws:// or wss://) on an authorized engagement.
- `xxe`: testing a web application for XML External Entity injection on an authorized engagement.

</details>

## Sous-skills

110 modules d'approfondissement sous 30 skills parentes à haute valeur, dans `skills/<domain>/<skill>/sub/<sub>/SKILL.md`. Une sous-skill porte le frontmatter standard plus un champ `parent:` et le squelette complet du corps, ainsi une grande skill comme `web-sqli` se divise en modules ciblés (`sqli-detection`, `sqli-union-extraction`, `sqli-blind`, `sqli-out-of-band`, `sqli-manual-fallback`, `sqlmap-automation`) qui ne se chargent qu'au besoin.

| Skill parente | Sous-skills | Nombre |
| --- | --- | --- |
| `ad-enumeration` | `gpo-analysis`, `kerberos-enum`, `ldap-enumeration`, `trust-mapping` | 4 |
| `api-security-testing` | `api-discovery`, `authz-testing`, `mass-assignment`, `rest-fuzzing` | 4 |
| `auth-attacks` | `credential-stuffing`, `mfa-bypass-testing`, `password-reset-abuse`, `session-hijacking` | 4 |
| `aws-enumeration` | `ec2-metadata-abuse`, `iam-enumeration`, `s3-enumeration` | 3 |
| `bloodhound-methodology` | `bloodhound-collection`, `bloodhound-custom-queries`, `bloodhound-path-analysis` | 3 |
| `bug-bounty-workflow` | `duplicate-avoidance`, `recon-for-bounty`, `report-writing-bounty` | 3 |
| `c2-fundamentals` | `c2-channel-setup`, `c2-opsec`, `c2-payload-staging` | 3 |
| `cloud-security-basics` | `cloud-asset-inventory`, `cloud-iam-review`, `cloud-logging-checks` | 3 |
| `code-reviewer` | `reviewer-auth-flaws`, `reviewer-crypto-misuse`, `reviewer-sqli-patterns`, `reviewer-xss-patterns` | 4 |
| `crypto-fundamentals` | `encoding-vs-encryption`, `hash-identification`, `tls-misconfig-checks` | 3 |
| `disk-forensics` | `deleted-file-carving`, `filesystem-timeline`, `partition-recovery` | 3 |
| `forensics-fundamentals` | `artifact-parsing`, `evidence-handling`, `timeline-basics` | 3 |
| `incident-playbooks` | `data-breach-playbook-run`, `phishing-playbook-run`, `ransomware-playbook-run` | 3 |
| `incident-response` | `ir-containment`, `ir-eradication`, `ir-lessons-learned`, `ir-scoping` | 4 |
| `kerberoasting` | `asrep-roast-execution`, `kerberoast-execution`, `ticket-analysis` | 3 |
| `linux-hardening` | `auditd-baseline`, `kernel-hardening`, `service-minimization`, `ssh-baseline` | 4 |
| `memory-forensics` | `malware-in-memory`, `process-memory-triage`, `volatility-workflow` | 3 |
| `network-pivoting` | `port-forwarding-chains`, `socks-proxies`, `ssh-pivoting` | 3 |
| `nmap-methodology` | `nmap-evasion`, `nmap-host-discovery`, `nmap-port-scanning`, `nmap-scripting`, `nmap-service-detection` | 5 |
| `osint-methodology` | `breach-data-osint`, `infra-osint`, `people-osint` | 3 |
| `password-attacks` | `dictionary-attacks`, `mask-attacks`, `password-spraying`, `rule-based-mangling` | 4 |
| `privesc-linux` | `container-breakout-checks`, `cron-abuse`, `kernel-exploits`, `sudo-misconfig`, `suid-binaries` | 5 |
| `privesc-windows` | `alwaysinstallelevated`, `dll-hijacking`, `token-impersonation`, `unquoted-service-paths` | 4 |
| `recon-active` | `dns-bruteforce`, `os-fingerprinting`, `port-service-enum`, `web-tech-fingerprint` | 4 |
| `rsa-attacks` | `rsa-common-mistakes`, `rsa-padding-oracles`, `rsa-small-exponent` | 3 |
| `secure-coding` | `authz-checks`, `input-validation-patterns`, `output-encoding`, `secret-handling` | 4 |
| `threat-hunting` | `baseline-deviation`, `hunt-with-sigma`, `hypothesis-hunting` | 3 |
| `web-sqli` | `sqli-blind`, `sqli-detection`, `sqli-manual-fallback`, `sqli-out-of-band`, `sqli-union-extraction`, `sqlmap-automation` | 6 |
| `web-xss` | `xss-csp-bypass`, `xss-dom`, `xss-filter-bypass`, `xss-reflected`, `xss-stored` | 5 |
| `webapp-pentest-methodology` | `pentest-exploitation-phase`, `pentest-mapping`, `pentest-reporting`, `pentest-scoping` | 4 |

Carte visuelle : [MINDMAP.md](../MINDMAP.md).

## Agents

25 opérateurs nommés dans [agents/](../agents/). Chacun lie skills et cerveaux, déclare un mode de mémoire, une politique d'escalade et des contraintes dures. Porte qualité : `scripts/score.py` doit noter chaque agent à 70 ou plus (la moyenne du dépôt est de 95,2).

| Agent | Rôle |
| --- | --- |
| `ad-attack-agent` | Cartographie les chemins d'attaque Active Directory et prouve l'escalade de privilèges depuis n'importe quel credential initial. |
| `ai-redteam-agent` | Casse les systèmes IA comme le font les vrais adversaires : par le prompt, les outils et les données. |
| `api-security-agent` | Casse les APIs au niveau objet, fonction et logique, puis le prouve avec des requêtes. |
| `binary-exploitation-agent` | Transforme les crashs de binaires compilés en exploits prouvés et contrôlés. |
| `bug-bounty-hunter-agent` | Chasse les primes méthodiquement et rédige des rapports acceptés et payés. |
| `c2-operator-agent` | Opère l'infrastructure C2 red team avec discipline, discrétion et responsabilité totale. |
| `cloud-attack-agent` | Trouve les mauvaises configurations cloud et prouve le chemin d'escalade de privilèges depuis n'importe quel credential initial. |
| `code-review-agent` | Trouve les failles de sécurité dans le code source et remet aux développeurs des findings corrigibles. |
| `crypto-analyst-agent` | Vérifie si la cryptographie est une protection réelle ou juste de la décoration. |
| `devsecops-agent` | Sécurise le pipeline, les conteneurs et la plateforme qui les exécute. |
| `forensics-agent` | Reconstitue ce qui s'est passé à partir des preuves numériques avec une chaîne de possession défendable. |
| `hardware-hacker-agent` | Ouvre le matériel et le firmware pour trouver ce que la couche logicielle cache. |
| `incident-commander-agent` | Dirige la réponse à l'incident de la déclaration à la reprise, en gardant chaque équipe coordonnée. |
| `malware-triage-agent` | Classifie vite les binaires suspects et extrait les indicateurs qui comptent. |
| `mobile-assessment-agent` | Teste les apps mobiles comme le ferait un attaquant avec l'APK et un appareil rooté. |
| `osint-agent` | Collecte et vérifie le renseignement de sources ouvertes, chaque affirmation étant sourcée. |
| `pentest-reporter-agent` | Transforme les findings bruts en rapports auxquels les dirigeants font confiance et que les développeurs peuvent appliquer. |
| `phishing-defense-agent` | Défend la couche humaine : analyse les phish, forme les utilisateurs et resserre les défenses e-mail. |
| `privacy-engineer-agent` | Intègre la confidentialité dans les systèmes : moins de données collectées, mieux protégées, traitement prouvable. |
| `purple-team-agent` | Joue les côtés rouge et bleu d'un exercice pour que les détections soient prouvées, pas supposées. |
| `recon-agent` | Transforme des cibles inconnues en inventaire cadré et fondé sur des preuves avant les tests actifs. |
| `secure-architect-agent` | Conçoit la sécurité dans les systèmes dès le départ et durcit l'existant. |
| `soc-analyst-agent` | Trie vite les alertes, sépare les vrais incidents du bruit et mène la réponse selon le playbook. |
| `threat-hunter-agent` | Chasse les adversaires cachés avec hypothèses, télémétrie et preuves, pas juste des alertes. |
| `web-exploitation-agent` | Prouve que les vulnérabilités web sont réelles en les exploitant en sécurité dans le périmètre et en documentant chaque étape. |

## Cerveaux

16 schémas de raisonnement réutilisables dans [brains/](../brains/). Les agents les composent : un agent offensif charge `attacker-mindset`, un agent de reporting charge `evidence-chain`, un agent de conception charge `threat-modeling`.

| Cerveau | Ce qu'il apporte |
| --- | --- |
| `assume-breach` | Concevoir ou opérer comme si l'adversaire était déjà à l'intérieur. |
| `attacker-mindset` | Raisonner comme un attaquant : planifier un pentest, prioriser les cibles, choisir quoi exploiter en premier. |
| `blast-radius-thinking` | Limiter la portée d'une défaillance en concevant les déploiements. |
| `cost-of-attack` | Penser en économie de l'attaquant : prioriser les vulnérabilités selon leur coût d'exploitation. |
| `defender-mindset` | Raisonner comme un défenseur : concevoir des contrôles, prioriser les correctifs à budget limité. |
| `detection-engineering-mindset` | Construire ou améliorer les détections : écrire des règles pour les attaques qui comptent. |
| `evidence-chain` | Prouver que quelque chose s'est passé et montrer son travail : chaque affirmation remonte à une source. |
| `hypothesis-driven-testing` | Tester au lieu de deviner : vérifier si une vulnérabilité est réelle avec des expériences. |
| `incident-command-mindset` | Diriger ou soutenir une réponse coordonnée : commander sous pression. |
| `least-privilege-design` | Concevoir ou revoir le contrôle d'accès : n'attribuer que les permissions nécessaires. |
| `opa-decision-loop` | Agir sous pression temporelle avec des informations incomplètes. |
| `root-cause-analysis` | Trouver pourquoi quelque chose a vraiment échoué : revue post-incident. |
| `scientific-debugging` | Trouver la cause d'un dysfonctionnement : reproduire d'abord, changer une variable à la fois. |
| `secure-defaults` | Choisir des valeurs par défaut sûres pour un système, un produit ou une configuration. |
| `threat-modeling` | Raisonner sur ce qui peut mal tourner avant que ça arrive : les actifs d'abord, frontières de confiance. |
| `zero-trust-reasoning` | Concevoir ou évaluer l'accès dans un monde sans réseau de confiance. |

## Système de mémoire

Les agents ont besoin d'une mémoire avec des règles, pas d'un tiroir fourre-tout. Trois documents plus un CLI :

- [memory/MEMORY_SCHEMA.md](../memory/MEMORY_SCHEMA.md) : les trois types de mémoire. Épisodique (événements horodatés, TTL de 30 jours), sémantique (faits durables), procédurale (comment les choses se font).
- [memory/LIFECYCLE.md](../memory/LIFECYCLE.md) : capture, consolidation et expiration. Les entrées dupliquées fusionnent, les périmées expirent.
- [memory/HYGIENE.md](../memory/HYGIENE.md) : règles d'hygiène qui gardent la mémoire petite, sourcée et digne de confiance.
- [tools/memory-store/](../tools/memory-store/) : `memory-store`, un petit CLI SQLite que les agents utilisent pour lire et écrire la mémoire. Chaque outil dans `tools/` est en bibliothèque standard uniquement et accepte `--help`.

![Flux de mémoire](../assets/memory-flow.svg)

## Documents de décision

Cinq documents de politique permanents dans [decisions/](../decisions/) que les agents consultent au lieu d'improviser :

| Document | Objet |
| --- | --- |
| `decisions/ESCALATION_POLICY.md` | Quand un agent doit s'arrêter et demander à un humain |
| `decisions/RISK_MATRIX.md` | Comment noter probabilité fois impact avant d'agir |
| `decisions/GO_NO_GO_GATES.md` | Les portes qui décident si un engagement continue |
| `decisions/ADR_TEMPLATE.md` | Modèle pour les registres de décisions d'architecture |
| `decisions/COST_BENEFIT.md` | Comment peser le coût de l'attaquant contre le coût du défenseur |

## Playbooks

8 guides d'engagement de bout en bout dans [playbooks/](../playbooks/). Chaque playbook lie agents, skills, cerveaux et documents de décision en phases ordonnées avec critères d'entrée et de sortie, rôles et passations, conditions d'arrêt et artefacts produits.

| Playbook | Exécutez-le quand... |
| --- | --- |
| `ad-assessment` | vous avez besoin d'un assessment de sécurité Active Directory, de l'énumération anonyme au mouvement latéral. |
| `bug-bounty-sprint` | vous devez mener un sprint de bug bounty ciblé et borné dans le temps contre le périmètre d'un programme. |
| `cloud-review` | vous avez besoin d'une revue de sécurité d'environnements AWS, Azure ou GCP, couvrant identité, configuration et logs. |
| `external-pentest` | vous avez besoin d'un pentest externe complet contre une entreprise dans le périmètre, de la surface publique au rapport. |
| `malware-outbreak` | un malware est suspecté ou confirmé dans l'environnement et vous avez besoin d'un triage et d'un confinement coordonnés. |
| `secure-sdlc-rollout` | vous devez déployer un cycle de vie de développement sécurisé dans une équipe d'ingénierie. |
| `soc-triage-day` | vous devez mener une journée complète de triage des opérations de sécurité, de l'entrée des alertes au rapport. |
| `webapp-assessment` | vous avez besoin d'un assessment de sécurité approfondi d'une application web et de ses APIs, de la modélisation des menaces au rapport. |

## Workflows

4 schémas de coordination multi-agents dans [workflows/](../workflows/) :

| Workflow | Schéma |
| --- | --- |
| `workflows/pipeline.md` | Étapes en séquence, chacune alimente la suivante |
| `workflows/coordinator-fanout.md` | Un coordinateur répartit les tâches aux travailleurs puis fusionne |
| `workflows/reviewer-gate.md` | Un relecteur doit approuver avant que l'étape suivante ne s'exécute |
| `workflows/evidence-gate.md` | Les affirmations n'avancent qu'avec des preuves jointes |

## Outils CLI

47 petits outils CLI Python dans [tools/](../tools/). Chaque outil utilise uniquement la bibliothèque standard de Python, accepte `--help` avec des exemples, quitte 0 en succès et 2 en erreurs d'usage, et est couvert par `scripts/test_tools.py`.

<details>
<summary><strong>Déplier le tableau complet des outils (47 outils)</strong></summary>

| Outil | Ce qu'il fait |
| --- | --- |
| port-scanner | Scan TCP de connexion d'un hôte à la recherche de ports ouverts (scannez seulement ce que vous pouvez tester) |
| banner-grabber | Se connecte à un port TCP et lit la bannière du service |
| hash-identifier | Devine le type d'un hash d'après son format (ne le casse jamais) |
| subnet-calculator | Affiche réseau, broadcast, masque et plage d'hôtes pour un CIDR |
| password-generator | Génère des mots de passe aléatoires avec le module secrets |
| base64-codec | Encode du texte en base64 ou décode du base64 en texte |
| hex-codec | Encode du texte en hex, décode du hex ou vide un fichier en hex |
| log-grep-analyzer | Cherche dans un log avec une regex et résume les correspondances |
| json-formatter | Joli-affichage, minification et validation de JSON |
| url-encoder | Encode, décode les URLs ou analyse une query string |
| jwt-decoder | Décode l'en-tête et le payload d'un JWT (ne vérifie PAS la signature) |
| dns-resolver | Résout les enregistrements A/AAAA ou fait une recherche inversée avec le résolveur système |
| http-header-checker | Récupère une URL et rapporte les en-têtes de réponse plus une checklist de sécurité |
| ssl-cert-checker | Affiche le certificat TLS d'un hôte : sujet, émetteur, dates, SANs |
| file-hasher | Hashe les fichiers avec MD5, SHA-1 et SHA-256 en lectures par blocs |
| string-extractor | Extrait les chaînes imprimables d'un binaire (un simple clone de strings) |
| cron-explainer | Explique une planification cron à cinq champs en langage clair |
| regex-tester | Teste une regex contre un texte et montre les correspondances et les groupes nommés |
| caesar-cipher | Encode, décode ou brute-force le chiffrement par décalage de César |
| rot13-codec | Applique ROT13 à un texte (encoder et décoder, c'est pareil) |
| morse-codec | Encode du texte en morse ou décode du morse en texte |
| uuid-generator | Génère des UUID (versions 1, 3, 4, 5) |
| timestamp-converter | Convertit les timestamps Unix en dates et les dates en timestamps |
| entropy-checker | Mesure l'entropie de Shannon d'un texte ou d'un fichier en bits par octet |
| csv-column-extractor | Extrait les colonnes CSV par nom ou index, avec déduplication et comptages |
| cidr-merger | Fusionne les plages CIDR qui se chevauchent ou adjacentes en ensemble minimal |
| port-list-expander | Étend une spécification de ports comme 80,443,8000-8005 en liste complète |
| http-status-lookup | Cherche la signification des codes de statut HTTP |
| unicode-inspector | Affiche codepoint, nom, catégorie et octets UTF-8 par caractère |
| checksum-verifier | Vérifie un fichier contre un checksum attendu (détecte l'algorithme) |
| diceware-generator | Construit une phrase de passe avec des mots aléatoires et le module secrets |
| totp-generator | Génère ou vérifie des codes TOTP (RFC 6238) depuis un secret base32 |
| email-header-analyzer | Analyse les en-têtes e-mail : adresses, sauts Received, signes d'usurpation |
| iban-validator | Valide les IBAN avec contrôle de format et checksum mod-97 |
| luhn-checker | Valide les nombres avec le checksum de Luhn ou calcule une clé de contrôle |
| semver-compare | Compare les versions sémantiques et teste des plages simples |
| crontab-validator | Valide les fichiers crontab : champs de temps, @specials et commandes |
| markdown-toc | Génère une table des matières depuis les titres Markdown |
| wordlist-mutator | Mute les entrées de wordlists : casse, leet, années, symboles, nombres |
| url-parser | Découpe une URL en parties et signale les traits suspects |
| phone-parser-basic | Normalise et inspecte un numéro de téléphone (analyseur heuristique basique) |
| color-converter | Convertit une couleur entre HEX, RGB et HSL |
| unit-converter | Convertit les unités de longueur, masse, température, taille de données et temps |
| random-sample-picker | Prend N éléments au hasard dans une liste, avec ou sans remise |
| text-stats | Compte lignes, mots, caractères et mots les plus fréquents d'un texte |
| diff-word | Affiche un diff au niveau du mot de deux fichiers texte |

</details>

## Qualité et benchmarks

La qualité se mesure, elle ne s'affirme pas. Deux portes de machines tournent en CI :

**Porte 1 : `scripts/validate.py` (14 contrôles).** Valide chaque skill, sous-skill, agent, cerveau, playbook et workflow : champs de frontmatter requis, nom correspondant au slug du dossier, descriptions denses en déclencheurs, versions semver, valeurs de cycle de vie valides, dates `last_verified` sensées, références de dépendances qui résolvent, graphe de dépendances acyclique, titres de corps requis (`## Quick Workflow`, `## Edge cases`, `## Key references`), arêtes `parent` des sous-skills, contrats des agents/cerveaux/playbooks, cohérence du manifeste et hygiène du contenu (pas de tirets em). Tout échec quitte non-zéro et fait échouer le build.

**Porte 2 : `scripts/score.py` (0 à 100).** Note chaque artefact sur la densité des déclencheurs, la qualité des commandes, les cas limites et les références. Fusionner exige 70 ou plus. Scores actuels du dépôt (de `scores.json`, 356 artefacts notés : 246 skills plus 110 sous-skills) :

| Métrique | Valeur |
| --- | --- |
| Artefacts notés | 356 (246 skills + 110 sous-skills) |
| Score moyen | 95,6 / 100 |
| Score le plus bas | 92 / 100 |
| Artefacts à 90+ | 356 (100 %) |
| Porte de fusion | 70+ |
| Moyenne des agents | 95,2 / 100 (25 agents, minimum 95) |

```diff
+ 100 % des artefacts notés dépassent 90+, loin au-dessus de la porte de fusion à 70
+ Zéro échec de validation : chaque dépendance résout, le graphe est acyclique
! Les scores mesurent la qualité de rédaction de la skill (déclencheurs, commandes, cas limites), pas le succès d'exploitation en direct
```

![Cycle de vie d'une skill](../assets/skill-lifecycle.svg)

## Parcours d'apprentissage

Parcours ordonnés dans le dépôt, de débutant à expert, chacun avec des jalons :

- [:green_book: Débutant](../docs/learning-paths/BEGINNER.md) : reco, Linux et premières attaques web. Jalon : mener un assessment d'application web cadré avec `webapp-assessment`.
- [:orange_book: Praticien](../docs/learning-paths/PRACTITIONER.md) : APIs, escalade de privilèges, Active Directory, triage de malware, workflows SOC. Jalon : mener une phase de pentest externe de bout en bout.
- [:closed_book: Expert](../docs/learning-paths/EXPERT.md) : attaques de confiance AD, exploitation de binaires, red teaming IA, ingénierie de détection, commandement d'incident. Jalon : diriger un exercice de purple team avec des détections prouvées.

![Parcours d'apprentissage](../assets/learning-path.svg)

## FAQ

<details>
<summary><strong>Déplier la FAQ (18 questions)</strong></summary>

### Qu'est-ce qu'une skill exactement ?
Un dossier avec un fichier `SKILL.md` : frontmatter YAML (nom, description déclencheuse, version, domaine, cycle de vie, dépendances) plus un corps avec Quick Workflow numéroté, procédures par phase avec commandes exactes, cas limites, chemins d'escalade, point de vue du défenseur et références clés. Les dossiers optionnels `scripts/`, `references/` et `assets/` l'accompagnent.

### Comment une skill se charge-t-elle dans mon agent ?
Divulgation progressive. Au démarrage de la session, l'agent ne voit que le nom et la description de chaque skill, ce qui ne coûte presque aucun contexte. Quand votre prompt correspond à une description, l'agent charge le corps complet. C'est pourquoi les descriptions sont écrites comme des déclencheurs denses "Use when ..." et pourquoi le scoreur note la densité des déclencheurs.

### Quelle est la différence entre skills, sous-skills, agents, cerveaux, playbooks et workflows ?
Les skills sont des procédures. Les sous-skills sont des modules d'approfondissement dans une skill parente. Les agents sont des opérateurs nommés qui lient skills et cerveaux en un rôle répétable. Les cerveaux sont des schémas de raisonnement réutilisables (attacker-mindset, evidence-chain). Les playbooks sont des guides d'engagement ordonnés avec phases et conditions d'arrêt. Les workflows sont des schémas de coordination multi-agents (pipeline, reviewer-gate).

### Quelles plateformes sont supportées ?
19 plateformes, un standard `SKILL.md` : Claude Code, OpenCode, Codex CLI, Gemini CLI, Cursor, GitHub Copilot, Amp, Goose, Cline, Roo Code, Kilo Code, Zed, Warp, Windsurf, Kiro, Qwen Code, Crush, Continue et Aider (extrait de pointeur via `AGENTS.md`, car Aider n'a pas de support des skills). Voir [Installation pour votre plateforme](#installation-pour-votre-plateforme).

### Comment installer seulement ce dont j'ai besoin ?
Utilisez l'installateur sélectif : `./install.sh --category web` pour un domaine, `./install.sh --version web-sqli@1.0.0` pour une skill épinglée. Les dépendances se résolvent seules depuis `arsenal-manifest.json`. Prévisualisez tout avec `--dry-run`.

### Que signifie le score de qualité ?
`scripts/score.py` note chaque artefact de 0 à 100 sur la densité des déclencheurs, la qualité des commandes, les cas limites et les références. Fusionner exige 70+. La moyenne du dépôt est de 95,6 et chaque artefact noté est à 92 ou plus. Il mesure la qualité de rédaction, pas le succès d'exploitation en direct.

### Comment les dépendances sont-elles gérées ?
Les skills déclarent `requires` (prérequis durs), `extends` (spécialisation) et `relates` (voir aussi). L'installateur résout toute la fermeture `requires` plus `extends` et installe toute la chaîne. La CI échoue sur les références pendantes ou les cycles.

### Puis-je l'utiliser hors ligne ?
Oui. `scripts/bundle.py` empaquette les skills en une seule archive portable avec manifeste pour les environnements isolés.

### Le contenu offensif est-il dans le périmètre ? Est-ce légal de l'utiliser ?
**Travail de sécurité autorisé uniquement.** Engagements red team avec autorisation écrite, programmes de bug bounty dans le périmètre, compétitions CTF, recherche en sécurité sur vos propres systèmes et labs d'entraînement. Voir [SECURITY.md](../SECURITY.md) pour la liste explicite des refus. Les agents portent des contraintes dures (par exemple : ne jamais scanner une infrastructure que vous n'êtes pas autorisé à tester) et la politique d'escalade décide quand un humain doit intervenir.

### Comment contribuer une skill ?
Lisez [CONTRIBUTING.md](../CONTRIBUTING.md) pour le standard de frontmatter et le squelette du corps, échafaudez avec `scripts/new_skill.py`, puis exécutez `scripts/validate.py` et `scripts/score.py` en local. Votre skill doit passer les 14 contrôles de validation et noter 70+ pour fusionner.

### Qu'est-ce qu'un playbook, et quand en exécuter un ?
Un playbook est une séquence opérationnelle fixe pour un engagement répétable : il lie agents, skills, cerveaux et documents de décision en phases ordonnées avec critères d'entrée/sortie, rôles et passations, conditions d'arrêt et artefacts produits. Exécutez-en un quand le travail est un engagement complet (assessment d'application web, assessment AD, journée de triage SOC), pas une seule technique.

### Comment fonctionne la mémoire de l'agent ?
La mémoire suit un schéma (épisodique, sémantique, procédurale), un cycle de vie (capture, consolidation, expiration) et des règles d'hygiène, dans `memory/`. Le CLI `memory-store` (SQLite, bibliothèque standard uniquement) est ce que les agents utilisent pour la lire et l'écrire. Les agents déclarent un mode de mémoire `stateless` ou `persistent` dans leur frontmatter.

### Comment annuler une installation ou une skill défectueuse ?
`install.sh` sauvegarde la cible avant chaque installation ; `./install.sh --rollback` restaure la sauvegarde la plus récente. Chaque release est un tag git plus une entrée de changelog, donc une skill défectueuse se révoque aussi proprement avec git.

### Que se passe-t-il quand une skill devient périmée ?
Chaque skill porte une date `last_verified`. La CI échoue sur les dates impossibles ou périmées, ce qui expose les vieilles skills comme des échecs de build au lieu d'une pourriture silencieuse. Les états de cycle de vie (`experimental`, `stable`, `deprecated`) vous disent à quoi faire confiance.

### Mon agent n'a pas de support des skills. Puis-je l'utiliser quand même ?
Oui. Pour Aider, `./install.sh --platform aider` affiche un extrait de pointeur pour `AGENTS.md`. Tout agent qui lit le markdown peut aussi charger directement un fichier de skill ; le contrat de frontmatter est du YAML simple et le corps est du markdown simple.

### En quoi est-ce différent des awesome lists et des autres dépôts de skills ?
Les awesome lists lient vers l'extérieur ; AgentArsenal livre les procédures. Les autres dépôts de skills livrent du markdown ; ce dépôt ajoute le versionnage par skill, un harnais CI à 14 contrôles, une notation qualité de 0 à 100 avec porte de fusion, un graphe de dépendances validé, le suivi de fraîcheur, les états de cycle de vie, les paquets hors ligne, la discipline de retour en arrière et un manifeste de marketplace. Voir le tableau comparatif et la bande en haut.

### Qui le maintient et comment est-ce versionné ?
Les releases sont des tags git avec entrées de changelog ([CHANGELOG.md](../CHANGELOG.md) suit Keep a Changelog et SemVer). Chaque skill est versionnée indépendamment dans son frontmatter, donc vous pouvez épingler exactement ce que vous avez installé.

### Où est le site de documentation navigable ?
Exécutez `python3 scripts/generate_docs.py` pour le construire, puis ouvrez `docs/index.html`. Il couvre tous les domaines et skills avec le graphe de dépendances et les scores de qualité.

</details>

## Statistiques du projet

Le dépôt contient actuellement **246 skills**, **110 sous-skills**, **25 agents**, **16 cerveaux**, **8 playbooks**, **4 workflows**, **47 outils CLI** et **19 plateformes supportées** (compté le 2026-10-23 ; le catalogue ci-dessus est régénéré depuis le manifeste).

| Artefact | Nombre | Emplacement | Signal de qualité |
| --- | --- | --- | --- |
| Skills | 246 | `skills/<domain>/<name>/SKILL.md` | moyenne 95,6/100, minimum 92 |
| Sous-skills | 110 | `skills/<domain>/<skill>/sub/<sub>/SKILL.md` | moyenne 95,6/100 |
| Agents | 25 | `agents/<name>/AGENT.md` | moyenne 95,2/100, minimum 95 |
| Cerveaux | 16 | `brains/<name>/BRAIN.md` | contrats validés |
| Playbooks | 8 | `playbooks/<name>/PLAYBOOK.md` | liaisons validées |
| Workflows | 4 | `workflows/*.md` | validés |
| Outils CLI | 47 | `tools/<tool>/<tool>.py` | stdlib uniquement, harnais de test |
| Plateformes | 19 | `platforms/PLATFORM_SUPPORT.md` | chemins de la doc des vendors |
| Documents de décision | 5 | `decisions/` | référencés par les agents |

## Feuille de route

Planifié, susceptible de changer. Les éléments arrivent quand ils passent les mêmes portes que tout le reste (14 contrôles de validation, score de qualité 70+).

- [ ] Automatisation de la fraîcheur : passages programmés de re-vérification qui rafraîchissent les dates `last_verified` avec preuves.
- [ ] Soumissions de skills de la communauté avec les mêmes portes CI pour les contributeurs externes.
- [ ] Recherche dans le site de documentation et pages d'historique de versions par skill.
- [ ] Plus de couverture de plateformes à mesure que de nouveaux CLIs d'agents adoptent le standard `SKILL.md`.
- [ ] Traductions des documents centraux (READMEs espagnol et français déjà dans `translations/`).
- [ ] Tutoriels vidéo : installation, premier chargement de skill et exécution complète d'un playbook.
- [ ] Serveur MCP exposant le catalogue de skills et memory-store aux clients MCP.

Les suggestions sont bienvenues en issues ou pull requests.

## Contribuer

Voir [CONTRIBUTING.md](../CONTRIBUTING.md) pour le standard de frontmatter, le squelette de corps que chaque skill doit suivre et comment ajouter une nouvelle skill avec `scripts/new_skill.py`. La version courte :

```bash
python3 scripts/new_skill.py --domain web --name my-skill   # échafaudage
# ... écrivez la skill ...
python3 scripts/validate.py   # doit passer les 14 contrôles
python3 scripts/score.py      # doit noter 70+
```

Règles : contenu original uniquement, travail de sécurité autorisé uniquement, anglais simple et direct, pas de tirets em dans le contenu (la CI cherche U+2014).

## Licence

MIT. Voir [LICENSE](../LICENSE).

## Remerciements

Construit avec du contenu original. Les idées d'infrastructure qu'il suit ont été apprises de deux projets sous licence MIT ; voir [ACKNOWLEDGEMENTS.md](../ACKNOWLEDGEMENTS.md) pour l'attribution complète et factuelle.
