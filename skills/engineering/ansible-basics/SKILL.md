---
name: ansible-basics
description: Use when automating server configuration with Ansible on an
  authorized engineering task. Covers inventory files, ad-hoc commands,
  playbook structure with plays tasks and handlers, idempotent modules,
  variables and vault-encrypted secrets, roles for reuse, and check mode
  plus diff for safe runs. Use when configuring fleets of Linux hosts,
  hardening servers repeatably, or replacing snowflake shell scripts with
  declarative automation.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [linux-hardening, git-workflows]
tools:
  - name: Ansible Core
    version: 2.18
---

Ansible configures machines over SSH with no agent to install: you
describe the desired state in YAML, and Ansible makes it so. This
skill covers inventory, ad-hoc commands for one-off tasks, playbooks
with idempotent modules, secrets with Vault, and roles for reuse. All
examples use Ansible Core 2.18 against Linux hosts you are authorized
to manage.

## Quick Workflow

1. Define the inventory: groups of hosts with connection variables.
2. Test connectivity with the `ping` module before running anything
   real.
3. Use ad-hoc commands for one-off checks; write playbooks for
   anything you will run twice.
4. Run every playbook first with `--check --diff` to preview changes.
5. Use idempotent modules (`apt`, `copy`, `template`, `service`)
   instead of `shell` wherever possible.
6. Encrypt secrets with `ansible-vault`; never store plaintext
   passwords in playbooks.
7. Organize repeated logic into roles with defaults, tasks, and
   handlers.
8. Keep playbooks in git and run production changes from a
   controlled runner, not a laptop.

## 1. Inventory and connectivity

```bash
ansible --version

mkdir ansible-demo && cd ansible-demo
cat > inventory.ini <<'EOF'
[web]
web1.example.com
web2.example.com

[db]
db1.example.com

[all:vars]
ansible_user=deployer
ansible_ssh_private_key_file=~/.ssh/deployer_ed25519
EOF

# The ping module tests the Ansible connection, not ICMP
ansible -i inventory.ini all -m ping

# Gather facts about every host (OS, IPs, memory, disks)
ansible -i inventory.ini web -m setup -a 'filter=ansible_distribution*'
```

Inventory groups (`web`, `db`) let you target subsets. Facts gathered
by the `setup` module are available as variables like
`ansible_distribution` in playbooks.

## 2. Ad-hoc commands for one-off work

```bash
# Check uptime everywhere
ansible -i inventory.ini all -a 'uptime'

# Install a package idempotently (nothing happens if already installed)
ansible -i inventory.ini web -m apt -a 'name=nginx state=present update_cache=yes' -b

# Copy a file with correct ownership and permissions
ansible -i inventory.ini web -m copy \
  -a 'src=./motd dest=/etc/motd owner=root group=root mode=0644' -b

# Restart a service only if needed
ansible -i inventory.ini web -m service -a 'name=nginx state=restarted' -b

# Run as a specific user without full become
ansible -i inventory.ini db -m command -a 'whoami' -b --become-user postgres
```

The `-b` flag enables privilege escalation (sudo). Ad-hoc commands
are for exploration and emergencies; repeatable work belongs in
playbooks.

## 3. First playbook

```bash
cat > site.yaml <<'EOF'
---
- name: Baseline web servers
  hosts: web
  become: true
  vars:
    admin_email: ops@example.com

  tasks:
    - name: Install nginx
      ansible.builtin.apt:
        name: nginx
        state: present
        update_cache: true

    - name: Deploy index page
      ansible.builtin.copy:
        content: "Hello from {{ inventory_hostname }}\n"
        dest: /var/www/html/index.html
        owner: www-data
        group: www-data
        mode: "0644"
      notify: Reload nginx

    - name: Ensure nginx is running and enabled
      ansible.builtin.service:
        name: nginx
        state: started
        enabled: true

  handlers:
    - name: Reload nginx
      ansible.builtin.service:
        name: nginx
        state: reloaded
EOF

# Preview first: check mode shows what WOULD change, diff shows how
ansible-playbook -i inventory.ini site.yaml --check --diff

# Then run for real
ansible-playbook -i inventory.ini site.yaml
```

Handlers run once at the end of the play, only when notified by a
task that actually changed something. This is how you avoid
restarting services on every run.

## 4. Templates and variables

```bash
mkdir -p templates
cat > templates/nginx.conf.j2 <<'EOF'
# Managed by Ansible: local edits will be overwritten
server {
    listen 80;
    server_name {{ inventory_hostname }};
    access_log /var/log/nginx/{{ inventory_hostname }}.access.log;

    location / {
        proxy_pass http://127.0.0.1:{{ app_port | default(8080) }};
    }
}
EOF

cat > webapp.yaml <<'EOF'
---
- name: Configure nginx vhost
  hosts: web
  become: true
  vars:
    app_port: 8080
  tasks:
    - name: Deploy vhost config from template
      ansible.builtin.template:
        src: templates/nginx.conf.j2
        dest: /etc/nginx/sites-enabled/app.conf
        owner: root
        group: root
        mode: "0644"
        validate: "nginx -t -c %s"
      notify: Reload nginx
  handlers:
    - name: Reload nginx
      ansible.builtin.service:
        name: nginx
        state: reloaded
EOF

ansible-playbook -i inventory.ini webapp.yaml --check --diff
```

The `validate` option checks the rendered config before installing
it; a bad template never reaches the live config directory. Jinja2
filters (`default`, `join`, `to_json`) handle missing variables
gracefully.

## 5. Vault for secrets

```bash
# Create a vault password file with strict permissions (or use a script)
openssl rand -hex 32 > ~/.vault_pass
chmod 600 ~/.vault_pass
export ANSIBLE_VAULT_PASSWORD_FILE=~/.vault_pass

# Create an encrypted variables file
ansible-vault create group_vars/db/vault.yaml
# inside the editor, write:
# db_password: "a-very-long-random-password"

# Encrypt an existing file, edit later without decrypting to disk
ansible-vault encrypt group_vars/db/secret_vars.yaml
ansible-vault edit group_vars/db/vault.yaml

# Use the secret in a playbook: {{ db_password }}
ansible-playbook -i inventory.ini db.yaml --ask-vault-pass
```

Vault encrypts with AES256. Store the vault password in a password
manager or CI secret, never next to the encrypted files. Rotate
secrets with `ansible-vault rekey` when someone with access leaves.

## 6. Roles for reuse

```bash
# Scaffold a role layout
ansible-galaxy role init roles/hardening
find roles/hardening -type f | sort

# Minimal role: defaults, tasks, handlers
cat > roles/hardening/defaults/main.yaml <<'EOF'
---
ssh_permit_root_login: "no"
ssh_password_auth: "no"
EOF

cat > roles/hardening/tasks/main.yaml <<'EOF'
---
- name: Harden sshd config
  ansible.builtin.lineinfile:
    path: /etc/ssh/sshd_config
    regexp: "{{ item.regexp }}"
    line: "{{ item.line }}"
    validate: "sshd -t -f %s"
  loop:
    - { regexp: '^#?PermitRootLogin', line: "PermitRootLogin {{ ssh_permit_root_login }}" }
    - { regexp: '^#?PasswordAuthentication', line: "PasswordAuthentication {{ ssh_password_auth }}" }
  notify: Restart sshd
EOF

cat > roles/hardening/handlers/main.yaml <<'EOF'
---
- name: Restart sshd
  ansible.builtin.service:
    name: ssh
    state: restarted
EOF

cat > harden.yaml <<'EOF'
---
- name: Harden all hosts
  hosts: all
  become: true
  roles:
    - hardening
EOF

ansible-playbook -i inventory.ini harden.yaml --check --diff
```

Roles separate defaults (overridable), tasks, handlers, templates,
and files. Pin third-party roles from Galaxy to a version; review
their tasks before running them with become on your fleet.

## Edge cases

- SSH fails with "Permission denied (publickey)". The key path in
  inventory is wrong or the key is not authorized on the host; test
  with plain `ssh -i key user@host` first to separate SSH problems
  from Ansible problems.
- Playbook hangs on gathering facts. A host has broken DNS or a
  stuck mount; run with `-e ansible_timeout=20` or disable fact
  gathering (`gather_facts: false`) for fact-free plays.
- `--check` mode reports changes for `shell` tasks every run. Shell
  and command tasks are not idempotent by default; add
  `creates:`/`removes:` guards or rewrite with a proper module.
- Handler never fires. The notifying task name must match the
  handler name exactly, and handlers only run on `changed`, not on
  `ok`; a task that reports changed every run masks this.
- Vault password prompt in CI. Set `ANSIBLE_VAULT_PASSWORD_FILE`
  to a script or file provided by the CI secret store; never commit
  the password file.
- `lineinfile` duplicates lines. The `regexp` did not match the
  existing line (commented variants, whitespace); test the regex
  against the real file and anchor it properly.
- Become asks for a sudo password on every host. Use
  `--ask-become-pass` interactively, or configure passwordless sudo
  for the automation user limited to the needed commands.

## Detection and defender view

For engineering skills this section covers detecting misuse and
misconfiguration. Ansible misuse shows up as playbooks with
`become: true` on every task, vault-encrypted files committed next
to their password file, and `shell:` tasks piping `curl` into
`bash` from the internet. Detect misconfiguration by reviewing
playbooks for hardcoded passwords (grep for `password:` outside
vault files), checking that the automation user has limited sudo
rights instead of `ALL=(ALL) NOPASSWD:ALL`, and auditing
`~/.ansible` logs for which hosts were touched and when. An
attacker with the vault password owns every secret in the repo, so
treat vault passwords like production credentials: rotate on
personnel changes and never share them in chat. Unexpected
`ansible-playbook` runs against production inventory outside change
windows deserve investigation.

## Key references

- Ansible Core 2.18 documentation: https://docs.ansible.com/
- Playbook guide: https://docs.ansible.com/ansible/latest/playbook_guide/index.html
- ansible-vault: https://docs.ansible.com/ansible/latest/vault_guide/index.html
- Built-in modules index: https://docs.ansible.com/ansible/latest/collections/ansible/builtin/
- CWE-798 (Use of Hard-coded Credentials): plaintext secrets in
  playbooks and inventory.
- CWE-732 (Incorrect Permission Assignment for Critical Resource):
  overly broad sudo for automation users.
