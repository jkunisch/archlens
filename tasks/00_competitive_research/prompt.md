# Competitive Research: Löst das wirklich niemand?

> **Zweck:** Validieren ob ArchLens wirklich eine Lücke füllt — oder ob existierende Tools das gleiche/bessere tun  
> **Empfohlene Quellen:** Perplexity, G2, GitHub, ProductHunt, Hacker News  
> **Ausgabe:** `tasks/00_competitive_research/RESEARCH_REPORT.md`

---

## Die konkrete Frage

**"Gibt es ein Tool das automatisch bei jedem GitHub PR einen Architecture-Graph difft, Boundary-Violations erkennt, und das Ergebnis als visuellen Kommentar im PR postet — ohne dass Quellcode den CI-Runner verlässt?"**

Antworte mit: JA (Tool X macht genau das), TEILWEISE (Tool X macht A und B aber nicht C), NEIN (niemand macht das vollständig).

---

## Zu prüfende Kandidaten (konkret, nicht allgemein)

### Kategorie 1: Architecture Analysis Tools
Prüfe **jedes** dieser Tools auf genau 4 Fragen:
- Baut es automatisch einen Graph (kein manuelles Modell)?
- Hat es native GitHub PR-Integration (Kommentar + CI Status)?
- Kann es Boundary-Violations als Regeln definieren (Config-as-Code)?
- Bleibt der Quellcode im CI-Runner (kein Cloud-Upload)?

| Tool | Prüfen |
|---|---|
| **Codescene** (codescene.com) | Architectural analysis, CI integration |
| **Embold** (embold.io) | Code structure analysis |
| **Teamscale** (teamscale.com) | Architecture conformance checking |
| **Structure101** (structure101.com) | Dependency analysis |
| **Lattix** (lattix.com) | Dependency structure matrix |
| **SonarQube** (sonarcloud.io) | Architecture rules via custom plugins |
| **NDepend** (.NET only) | Architecture validation |

### Kategorie 2: Linter-basierte Enforcement Tools
Diese Tools erzwingen Regeln statisch — kein Graph, kein Diff. Prüfe ob sie das Boiling Frog Problem lösen:

| Tool | Sprache | Was sie können | Was sie NICHT können |
|---|---|---|---|
| `eslint-plugin-boundaries` | JS/TS | `forbid: frontend → db` als statische Regel | Kein Graph, kein Diff, kein Blast Radius, keine History |
| `dependency-cruiser` | JS/TS | Dependency Diagramme + verbotene Deps | Kein PR-Diff, kein Cluster-Auto-Detection |
| `ArchUnit` | Java | Unit-Tests für Architektur-Regeln | Kein Graph-Diff, kein visueller Output im PR |
| `Forbidden Island` | Python | Import-Verbote | Nur Imports, kein Graph |
| `import-linter` | Python | Layer-Checks | Kein Diff, kein Blast Radius |

**Kernfrage:** Können diese Tools warnen "dieser Node mutiert über die letzten 12 PRs schleichend zum God Node" (Boiling Frog)? Wenn nein → haben wir eine echte Lücke.

### Kategorie 3: AI-native Developer Tools mit Architecture Features
| Tool | Prüfen |
|---|---|
| **Sourcegraph** | Hat es Architecture-Graph-Diff? Oder nur Symbol-Search? |
| **CodeAnt AI** | Architectural analysis in PRs? |
| **Moderne** (moderne.io) | Automated refactoring — hat es Architecture Diff? |
| **DX (getdx.com)** | Engineering metrics — Architecture Health Score? |

### Kategorie 4: Neue Startups / GitHub Marketplace Apps
- Suche auf **GitHub Marketplace** nach: "architecture", "dependency graph", "code structure"
- Suche auf **ProductHunt** (letzten 12 Monate): "architecture drift", "code health", "dependency analysis"
- Suche auf **Hacker News** (Ask HN / Show HN): "architecture drift detection", "PR architecture check"

---

## Was du für jeden Kandidaten dokumentierst

```markdown
### [Tool Name]
- **URL:** 
- **Pricing:** 
- **Automatischer Graph-Build:** Ja / Nein / Teilweise
- **GitHub PR Integration:** Ja / Nein / Teilweise  
- **Config-as-Code Regeln:** Ja / Nein / Teilweise
- **Zero-Code-Egress:** Ja / Nein
- **Boiling Frog / Trend-Erkennung:** Ja / Nein
- **Kritische Lücke gegenüber ArchLens:** [1-2 Sätze]
```

---

## Ausgabe-Format

Erstelle `tasks/00_competitive_research/RESEARCH_REPORT.md` mit:

1. **Executive Summary** (5 Sätze): Löst das jemand? Was ist die echte Lücke?
2. **Vollständige Kandidaten-Tabelle** (alle geprüften Tools)
3. **Dangerous Competitors** — Tools die ArchLens ernsthaft gefährden könnten
4. **Safe Zones** — Bereiche wo ArchLens klar allein ist
5. **Go/No-Go Empfehlung** basierend auf Competitive Landscape

---

> Wenn du einen Tool findest der **alle 4 Kriterien** erfüllt (Auto-Graph, PR-Integration, Config-as-Code, Zero-Egress): Stoppe sofort und schreibe das in den Executive Summary. Das wäre ein fundamentales Problem für ArchLens.
