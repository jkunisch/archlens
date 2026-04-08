# Security Research Prompt — Ethical Hacking & Vulnerability Detection

> **Zweck:** Recherche der besten Open-Source- und kommerziellen Tools zur Schwachstellenerkennung, Penetrationstests und Systemhärtung. Ziel ist defensives Sicherheitswissen — kein offensiver Missbrauch.

---

## Prompt (an Research-Agent übergeben)

```
You are a senior application security engineer and ethical hacking educator.
Your task is to research and curate the BEST toolset for someone who wants to
learn offensive security techniques in order to DEFEND systems better
(i.e., "think like an attacker to protect like a defender").

Focus exclusively on:
1. Legal, ethical, and defensive use cases
2. Tools that are industry-standard (used in CTFs, bug bounty programs, or pentests)
3. Open-source tools available on GitHub where possible
4. Clear categorization by attack surface / use case

---

## Research Targets

For EACH category below, find and document:
- Tool name + GitHub URL (if open source) or official website
- What vulnerability / attack surface it covers
- Skill level required (Beginner / Intermediate / Advanced)
- Best learning resource (course, CTF platform, YouTube channel, or docs)
- Whether it applies to Web Apps, Networks, APIs, CI/CD, or Cloud

---

## Categories to Cover

### 1. Web Application Security
Focus: OWASP Top 10, SQL Injection, XSS, CSRF, Auth bypass, JWT attacks
- Request: Best scanners, proxies, and fuzzing tools
- Example tools to verify: Burp Suite, OWASP ZAP, sqlmap, ffuf, nikto, dalfox

### 2. Network & Infrastructure Security
Focus: Port scanning, service enumeration, MITM, network sniffing, firewall auditing
- Example tools to verify: nmap, Wireshark, netcat, masscan, tcpdump, arp-scan

### 3. Vulnerability Scanning & CVE Detection
Focus: Automated finding of known CVEs in dependencies and running services
- Example tools to verify: Nuclei (ProjectDiscovery), OpenVAS, Nessus (free tier), Trivy

### 4. API Security Testing
Focus: REST/GraphQL endpoint testing, auth token abuse, rate limiting bypass
- Example tools to verify: Postman (security features), Hoppscotch, GraphQL Voyager,
  OWASP APISecurityTop10, kiterunner

### 5. Stress Testing & Load Security
Focus: DDoS simulation (for own infra), service resilience, rate limiting validation
- Example tools to verify: k6, Locust, Apache JMeter, vegeta, slowloris (educational)

### 6. Exploitation Frameworks
Focus: Controlled environment exploitation for learning (labs, CTFs, own VMs only)
- Example tools to verify: Metasploit Framework, Exploit-DB, searchsploit, pwntools

### 7. CI/CD & Supply Chain Security
Focus: Secret detection in repos, dependency confusion, SAST/DAST in pipelines
- Example tools to verify: Semgrep, Gitleaks, truffleHog, Snyk, Dependabot, OWASP
  Dependency-Check

### 8. Cloud & Container Security
Focus: Misconfiguration detection in AWS/GCP/Azure, Docker/K8s escape vectors
- Example tools to verify: Prowler, ScoutSuite, Trivy, Falco, kube-bench, Pacu

### 9. Password & Auth Security
Focus: Hash cracking (own systems), brute-force testing, credential stuffing simulations
- Example tools to verify: Hashcat, John the Ripper, Hydra (local labs only), CeWL

### 10. Social Engineering & Phishing Simulation (Defensive)
Focus: Awareness training toolkits for organizations testing their own employees
- Example tools to verify: GoPhish, SET (Social-Engineer Toolkit)

---

## Output Format

Return a structured Markdown table per category:

| Tool | GitHub / URL | Attack Surface | Skill Level | Best Resource |
|------|-------------|----------------|-------------|---------------|
| ...  | ...         | ...            | ...         | ...           |

Then provide:
1. **Recommended Learning Path** (step-by-step, beginner to advanced)
2. **Top 5 CTF Platforms** for practicing legally (HackTheBox, TryHackMe, PentesterLab, etc.)
3. **Top 3 YouTube Channels or Courses** for each major area
4. **Key certifications** to pursue (CEH, OSCP, eJPT, CompTIA Security+)
5. **GitHub Awesome Lists** relevant to each category (e.g., awesome-hacking, awesome-pentest)

---

## Constraints

- ONLY include tools legal to use on systems you own or have explicit written permission to test
- Flag any tool that has potential for misuse with a warning note
- Prioritize tools with active GitHub communities (>1k stars, commits in last 6 months)
- Include Dockerized / sandboxed variants where possible for safe local testing
- Focus on tools that cover the OWASP Testing Guide methodology
```

---

## Kontext: Warum diese Tools für ArchLens relevant sind

Für das ArchLens-Projekt sind insbesondere folgende Kategorien direkt relevant:

| Kategorie | Relevanz für ArchLens |
|-----------|----------------------|
| **CI/CD Security (SAST)** | Semgrep, Gitleaks — können direkt in unsere GitHub Action integriert werden |
| **API Security** | Das ArchLens-API (FastAPI) muss gegen Auth-Bypass und Injection getestet sein |
| **Dependency Scanning** | Trivy / Snyk für unsere Action-Docker-Container |
| **Vulnerability Scanning** | Nuclei für eigene Infrastruktur vor Go-Live |

---

## Nächste Schritte nach der Recherche

- [ ] Top-Tool pro Kategorie identifizieren
- [ ] Lernpfad dokumentieren (3–6 Monate Curriculum)
- [ ] CI/CD-Security-Tools in ArchLens Action integrieren (Task 03)
- [ ] Eigene Lab-VM aufsetzen (Kali Linux / Parrot OS)
- [ ] Ersten CTF auf HackTheBox oder TryHackMe lösen
