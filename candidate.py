"""Candidate profile, scoring rubric and canonical facts (module name avoids the stdlib `profile`).

Sources: the Claude artifact "Job Match Board" (profile, outcome calibration,
Fit/Win rubric, keyword buckets, LinkedIn launcher) and the Lovable app
"Job Search & Match Score Pro" (canonical facts and drafting rules for
application materials). Data only, no logic.
"""

CANDIDATE = "Ayhan Demir"

PROFILE = """CANDIDATE: Ayhan Demir. His own canonical title is "Process Excellence Senior Advisor" (Senior Advisor, not Director), which reflects real career facts: 8 years at Amazon were influence-based and advisory at scale, without direct ownership of a large P&L, a large headcount, or a large discretionary budget. PRIMARY TARGETS, genuinely at his level: Head of and Senior Manager roles with a real end-to-end mandate over a function or programme. Senior technical expert / Principal individual-contributor titles also fit cleanly.
DIRECTOR IS A REAL STRETCH, NOT A DEFAULT FIT: score a Director posting on its actual substance. If the posting explicitly asks for P&L ownership, a large team headcount, or multi-year budget authority, treat that as a genuine gap and say so plainly in gaps. If a "Director" posting actually describes Head-of-scale, single-function, advisory-plus-delivery work, it can score as a strong fit on substance; judge the job description, not the label. Never a fit below Senior Manager or senior technical expert.
19 years experience. 2018-2026 Amazon EU/WW Customer Service, two promotions to Single-Threaded Leader scope in Process Excellence (WW CS ACES). NEVER use internal level codes such as L4, L5 or L6 in any text you return; say "Single-Threaded Leader scope" instead. 2009-2018 Arcelik/Beko manufacturing quality engineering. Degree in Mechanical Engineering.
CORE DISCIPLINE: Process Excellence, Operational Excellence, Continuous Improvement, Lean Six Sigma Black Belt, DMAIC, Value Stream Mapping, Kaizen, statistical analysis (Minitab expert, regression, SPC, hypothesis testing), Programme and Project Management, Stakeholder Management, governance and operating-model design, delivering measured business outcomes.
SECONDARY STRENGTHS: AI Strategy and Digital Transformation at leadership level (Generative AI, LLM, prompt engineering, agentic AI concepts; sole designer of AuditAI, a GenAI audit system validated at 93.5% accuracy), and People/Culture/Wellbeing leadership (founded a mental-health affinity group).
DOMAIN BACKGROUND: large-scale operations and customer service/experience, plus earlier manufacturing quality.
VOICE OF THE CUSTOMER IS HIS CAREER, NEVER A GAP: all 8 Amazon years were spent in Customer Experience, turning customer contacts, defects and concessions into root causes and fixes, and presenting the cost of poor customer experience to the teams who own it. Amazon's internal vocabulary for it is contact drivers, defect elimination, CX signals, concession and refund reduction, and business reviews; outside Amazon the same discipline is called Voice of the Customer. A posting asking for VoC programme experience, customer insight programmes or customer feedback loops is a MATCH and belongs in strong. The only legitimate point is a labelling one: he should mirror the posting's wording.
NOT A FIT FOR (score these low even when the industry matches): software or embedded engineering, hands-on coding, systems/hardware/solution architecture (MBSE, cloud-native architecture, cyber-security architecture, IoT/edge/digital-twin engineering, MES/IT-OT target-architecture design), and pure sales or account management. He leads process, operational, and programme improvement; he does not design technical system architectures or write code.
LANGUAGES: English C2 fluent. German B1+ conversational, not business-fluent. Roles requiring fluent, business, native, verhandlungssicher, or C1/C2 German are a real barrier to flag. He prefers an English working environment.
LOCATION: Berlin. Wants Berlin-based, hybrid, or remote-EU.
TITLE SIGNALS AT TARGET LEVEL: Head of, Senior Manager, Continuous Improvement Lead, Transformation Lead, senior Expert, Staff, Principal. Director is a signal worth reading closely, not a default match.
HIS FIVE PILLARS (map each job to the closest, return the short name): P1 Strategic Leadership & Business Alignment; P2 Portfolio Design & Delivery; P3 Process Excellence & Lean Six Sigma; P4 AI Strategy & Digital Transformation; P5 People, Culture & Organisational Capability.
HIS ROLE IDENTITIES, most frequent first (pick the closest for fitRole): Continuous Improvement Lead; Head of Process Excellence; Head of Operations; Process Excellence Advisor; Head of AI Strategy; Senior Manager, Process Excellence; Head of Continuous Improvement; Senior Program Manager; Digital Transformation Lead; Head of Quality / CX; Head of Programs; Head of People / Culture; Strategy & Governance Lead.
HIS SIGNATURE PROJECTS (cite 1-3 by short name): AuditAI (GenAI audit automation, 93.5% accuracy); Concession Permission Clean-Up (access governance, $132M GCV finance-validated); VSO / IXD-FC (value stream optimization governance, $2.1B opportunity identified); BUWG Kaizen (SLA +80%); ACES Value Offers Framework (portfolio and operating-model design); PLS Multi-Phase Programme (programme delivery); Mail Label Fraud (fraud analytics, loss prevention); Mental Health & Wellbeing Affinity Group (people and culture leadership)."""

OUTCOME_CALIBRATION = """OUTCOME CALIBRATION, from his own real results as of October 2026. This is the most important section; read it before scoring anything.
THE RECORD, IN CONTEXT: 21 applications submitted. 16 concluded as rejections, 0 offers, 5 still live. 21 applications at Senior Manager and Head of level would typically produce two to four screens, about one final round, and zero to one offers. He reached a final round at Wolt as runner-up of 17 after four rounds. His conversion is roughly par for the volume. The binding constraint is how few suitable roles exist at this level in Berlin, not a broken candidacy, so never mark a posting down merely because the record shows no offer yet.
WHAT THE PREVIOUS RUBRIC GOT WRONG, measured against those outcomes:
- It rated disciplineFit "strong" on 19 of the 21 applications. A strong discipline match carries no information about whether he actually wins.
- Rejected and still-live applications had the same number of listed strengths and gaps. The assessments looked the same whatever the outcome.
- The highest score on the board, 88, was a rejection. Four of the five applications scoring 82 or above were rejections.
- Thin applicant counts predicted nothing. Treat a small applicant count as weak evidence, never as a reason for a high score.
- The one documented rejection reason, Wolt Senior Program Manager, October 2026: the panel judged another candidate slightly stronger on executive-level stakeholder management, influencing without authority, and finding a path forward with incomplete data. He was NOT beaten on process excellence, DMAIC, or domain knowledge.
WHAT THIS MEANS: at Senior Manager and Head of level in Berlin, process-excellence credentials are table stakes, because essentially every shortlisted candidate has them. He is losing on seniority signal: executive presence, evidence of moving senior stakeholders without formal authority, and visible decisiveness on incomplete data. Score with that in front of you."""

RUBRIC = """HOW TO WORK, in the order of the output fields:
1. requirement_matches: for every requirement R#, decide direct / adjacent / argued / missing from the EVIDENCE PACK only, and cite the evidence ids [E#] you used. "direct" means a named, quantified project that IS that thing; "adjacent" a closely related one; "argued" only a reasoned case; "missing" no support.
2. strong, reframeable, gaps, blockers: build them from step 1. Every strong and reframeable point cites at least one evidence id. Blockers are only the gaps that cost him the role: kind "screen" = a recruiter filters him out before anyone reads his case; "argue" = he can contest it in an interview.
3. evidence: for the role's single most important ask, is his best proof direct, adjacent or argued.
4. fit and win last, computed FROM the lists above, never first and justified after.

TWO SEPARATE NUMBERS. Do not let one pull the other. They often differ by 20 points or more, and when they do, that gap is the most useful thing in the assessment.

"fit" answers: how well does this role match what he does and wants? 85+ requires at most one minor gap; 65-84 allows two or three real but addressable gaps; 40-64 means several genuine gaps or a level or domain mismatch; below 40 means a fundamental mismatch on discipline or level, or a hard blocker such as language, location, or licensure. Weight disciplineFit most, then level, then language and location. Head of and Senior Manager titles with real scope are his bullseye. A domain-adjacent role that is really a technical architecture, software, or sales role scores low.

"win" answers a different question: WHERE DOES HE LAND IN THE STACK? It is standing, not probability. Place him against the four to six people who will make the shortlist, all of whom clear the discipline bar at this level. Score only what separates him from them.
 - Hard screens first. A requirement he objectively does not meet and cannot argue (C1 or C2 German, named P&L ownership, a stated direct-headcount minimum, a required licence or certification, a minimum number of years in a named industry, hands-on SQL or coding as daily work) caps win at 25 no matter how high the fit. Put it in blockers with kind "screen".
 - Evidence depth. "direct" supports a high win. "adjacent" and "argued" do not, because the others on that shortlist will have done the actual thing.
 - Seniority signal. If the posting leans on executive presence, board or C-level exposure, influencing without authority at scale, or deciding on incomplete data, treat that as a RISK rather than a strength, because it is the documented reason he has lost. Say so in winWhy.
 - Scarcity. Lean Six Sigma plus large-tech operations experience in Berlin is a deep candidate pool. The rarer his specific combination is for this posting, the higher the win.
 - Bands: 78-100 he is, or demonstrably was, the candidate to beat; reserve this for evidence rather than inference. 55-77 makes the shortlist and is in genuine contention. 35-54 is read seriously but likely out-competed by a more exact profile. 15-34 is one named screen he can sometimes talk past, or an undifferentiated profile in a deep pool. Below 15 is a hard screen where he does not compete.
 - Weighting that produced the existing scores, for consistency: start around 55, add about 15 for direct evidence and subtract about 10 for an argued case, subtract about 26 for the first named screen and 11 for each one after it, subtract about 7 where the role is levelled below his target. A posting on its own almost never justifies more than 70.

"winWhy" names the specific rival profile that beats him here, or the specific screen that stops him, for example "an internal candidate already running this function" or "a Big-4 manager with client-facing P&L". Never a generic sentence that would fit any posting.

EVIDENCE RULES: claims about his record come only from the EVIDENCE PACK or the profile above; never invent a project, figure or employer. Never mention the ACES AI Strategy or any AI strategy he authored for an organisation; his AI work is described through AuditAI and applied practice. Never use internal level codes (L4 to L7).

Be honest and do not inflate. A generous number sitting on a thin blockers list is exactly the failure mode that produced 21 applications and 0 offers."""

DECOMPOSE_PROMPT = """You read job postings (German or English, often copied from LinkedIn) for an executive search team.
Extract the posting's facts and break it into its 4 to 7 most important requirements, most important first.
For each requirement write evidence_query: one sentence in English describing the proof a strong candidate's record would contain, written the way a CV or case study would phrase it (this is used to search the candidate's portfolio).
List as screens only hard requirements that filter candidates out (language level, licence, P&L or headcount minimum, years in a named industry, hands-on coding)."""

# Canonical record from the Lovable app. It outranks every retrieved document.
CANONICAL_FACTS = """CANONICAL CANDIDATE RECORD. Verified and locked. These facts take precedence over anything retrieved. Figures are exact: never round, blend, recalculate or combine them.
NAME: Ayhan Demir. Berlin, Germany. German and EU citizen, dual with Turkish nationality. Hybrid preferred, remote EU acceptable.
CANONICAL TITLE: Process Excellence Senior Advisor.
EDUCATION: BSc Mechanical Engineering, Yildiz Technical University, 2003 to 2007.
EMPLOYMENT, most recent first. Job titles are exact and must be used as written:
- Amazon EU/WW Customer Service, 2018 to 2026. Title: Process Excellence Senior Advisor, WW CS ACES. Two promotions to Single-Threaded Leader scope. Three times Exceeds High Bar, three times Highly Valued.
- Arcelik A.S. (Beko), Washing Machine Plant, Istanbul, 2009 to 2018. Final title: Senior Specialist Engineer, Project Management. Led the quality department investment portfolio, was project leader for the quality systems of the new Arcelik plant in Romania, and held responsibility for a 48-person department, being 46 blue collar and 2 white collar staff.
- Total Teknik Ltd. Sti., Istanbul, 2007 to 2009. Title: Project Manager and Engineer. HVAC, heating, cooling, plumbing and fire or sprinkler system design for commercial and retail projects.
19 years of experience in total.
LOCKED FIGURES, restate exactly:
- $147MM+ confirmed and finance-validated total impact across eight years at Amazon.
- $132M, access governance, the Concession Permission Clean-Up. One figure only.
- $85M, Mail Label Fraud exposure closed, coordinated across five internal functions plus Apple and DHL externally.
- $2.1B, the IXD-FC packing gap. IDENTIFIED OPPORTUNITY ONLY, never part of the confirmed total.
- Up to $8B, the broader IXD-FC estimate. Always labelled "broader estimate".
- 93.5%, AuditAI validated accuracy across 10,000 contacts; AuditAI also cut the audit SLA 70% (7 days to 2).
- 80%, BUWG Kaizen: the Back-Up Work Group activation SLA improvement. A separate project from AuditAI; never attribute it to AuditAI.
- $15MM annualised, PLS (Product Life Support) Multi-Phase Programme, with a 45% SLA gain.
ACRONYMS, expand exactly as written: ACES = Amazon Customer Excellence System; BUWG = Back-Up Work Group; PLS = Product Life Support; IXD-FC = Inventory Exchange Dock, Fulfilment Centre; VSO = Value Stream Optimisation; CCX = Customer Contact Experience; STL = Single-Threaded Leader; GCV = Gross Concession Value; SLA = Service Level Agreement; DMAIC = Define, Measure, Analyse, Improve, Control.
PEOPLE LEADERSHIP, only in these two forms: the 48-person Arcelik department, and the 26-member Amazon wellbeing board.
WELLBEING GROUP: founded the Customer Service Mental Health Wellbeing Affinity Group, 2021 to 2024, as Founder, President and Worldwide Programme Lead. Co-led recruitment and training of a 26-member board. Stress scores improved from 3.8 to 2.3 in the first year. NEVER write "VP" for this role.
CERTIFICATIONS: Lean Six Sigma Black Belt. Certified Mental Health Ally.
AWARDS: Once CS Award, twice. Toy Yoda Kaizen Award. Hackacon Winner 2023 and 2025.
LANGUAGES: English C2. German B1+, conversational and not business fluent. Turkish native. Persian native."""

MATERIALS_RULES = """HARD RULES:
- Never invent, estimate, round, or infer any fact, figure, employer, title, date, or credential that is not in the canonical record or the evidence pack. If something needed is missing, leave it out and record it in notes.
- Never mention any AI strategy he authored or owned for an organisation, under any wording (including ACES AI Strategy and Hoshin Kanri). His AI work is described through AuditAI and applied practice only.
- The $2.1B packing gap and the up to $8B estimate are findings, not money saved: use only identified, quantified, sized, surfaced or modelled with them. $147MM+, $132M and $85M are confirmed and may take delivery verbs.
- No date of birth, age, marital status, address, photograph or ID number. Contact details: name, city, email.
- AI work is prompt engineering and structured process design, never backend engineering: do not write that he coded or engineered backend systems.
- No em dashes anywhere. Use commas, periods, or the word "and".
- No superlatives such as "the only" or "unparalleled". Never "passionate about", "team player", "responsible for".
- Executive first-person register with active verbs. Spell out every acronym on first use.
- Cover letter: one page, 250 to 330 words, one brief career trajectory line.
- CV: at most 4 experience entries with at most 5 bullets each. Every entry carries its real date range. Education is always populated.
- Include all three employers when the role values the engineering and manufacturing background; Amazon alone when it is purely technology, operations or e-commerce. State the choice and why as the first note."""

# ---------- keyword buckets (artifact offline scorer, also used to tag chunks) ----------
BUCKETS = [
    ("p3", "Process Excellence & Lean Six Sigma", 30, [
        "lean six sigma", "six sigma", "dmaic", "continuous improvement", "black belt", "kaizen", "spc",
        "minitab", "root cause", "regression", "value stream", "vsm", "process improvement", "process mapping",
        "operational excellence", "process standardis", "hoshin", "design of experiments", "doe",
        "hypothesis testing", "quality system", "iso 9001", "5s", "tpm", "gap analysis", "lean"]),
    ("p1", "Strategic Leadership & Business Alignment", 20, [
        "strategic leadership", "strategic planning", "stakeholder management", "stakeholder engagement",
        "cross-functional", "cross functional", "business case", "investment prioriti", "risk management",
        "single-threaded", "business alignment", "director-scope", "leadership"]),
    ("p4", "AI Strategy & Digital Transformation", 18, [
        "ai strategy", "generative ai", "genai", "llm", "large language model", "agentic", "prompt engineering",
        "machine learning", "digital transformation", "automation", "industry 4.0", "data-driven", "artificial intelligence"]),
    ("p2", "Portfolio & Programme Delivery", 17, [
        "programme management", "program management", "project management", "portfolio management",
        "portfolio delivery", "operating model", "governance", "change management", "prioritis", "pmo"]),
    ("p5", "People, Culture, MH & Employee Experience", 8, [
        "capability building", "talent development", "people development", "org design", "organisational design",
        "organizational design", "culture", "succession", "coaching", "ways of working", "organisational change",
        "organizational change", "mental health", "wellbeing", "employee experience", "people & culture", "people and culture"]),
    ("dom", "Domain adjacency", 7, [
        "customer experience", "customer service", "cost reduction", "compliance", "manufacturing", "returns",
        "contact reduction", "revenue protection", "loss prevention", "fraud"]),
]
PILLAR_SHORT = {"p3": "Process Excellence", "p1": "Strategic Leadership", "p4": "AI Strategy",
                "p2": "Portfolio & Delivery", "p5": "People & Culture", "dom": "Domain"}
ENGLISH_WORKING = ["english is the working language", "working language is english", "working language: english",
                   "english-speaking", "english speaking environment", "we work in english", "company language is english",
                   "fluent english", "business english", "business-level english", "english fluent", "english as working"]
GERMAN_REQUIRED = ["fluent german", "german c1", "german c2", "c1 german", "c2 german", "verhandlungssicher",
                   "muttersprache", "native german", "sehr gute deutsch", "gute deutschkenntnisse", "deutschkenntnisse",
                   "german is required", "german required", "german (native)", "fließend deutsch", "german: fluent"]
JUNIOR = ["junior", "entry-level", "entry level", "graduate", "intern ", "internship", "working student",
          "werkstudent", "praktikum", "trainee", "apprentice", "0-2 years", "1-2 years", "ausbildung", "duales studium"]
SENIOR = ["head of", "director", "principal", "vice president", " vp ", "chief", "senior manager", "senior ",
          " staff ", "expert", "lead", "technical manager", "team lead", "manager", "transformation"]
BERLIN_OK = ["berlin", "remote", "hybrid", "home office", "homeoffice", "anywhere", "deutschlandweit"]
GERMAN_WORDS = [" und ", " der ", " die ", " das ", " mit ", " für ", " sie ", " wir ", " von ", " im ", " bei ",
                " eine ", " sind ", " werden ", " sowie ", " oder ", " auch ", " aufgaben", " kenntnisse", " erfahrung"]
EXCLUDE_TITLES = ["account executive", "sales representative", "sales manager", "sales development",
                  "business development representative", "sdr", "bdr", "software engineer", "software developer",
                  "backend developer", "frontend developer", "full stack developer", "mobile developer"]

# ---------- signature projects: aliases used to tag chunks ----------
SIGNATURE_PROJECTS = {
    "AuditAI": ["auditai", "transpect", "transcribiwise", "transcript-analysis", "audit turnaround"],
    "Concession Permission Clean-Up": ["concession permission", "concession clean-up", "concession context", "ldap",
                                       "over-permission", "over-permissioned", "permission groups", "access-control groups"],
    "VSO / IXD-FC": ["vso", "value stream optimisation", "value stream optimization", "ixd-fc", "packing gap"],
    "BUWG Kaizen": ["buwg", "back-up work group", "activation flow"],
    "ACES Value Offers Framework": ["value offers"],
    "PLS Multi-Phase Programme": ["pls", "product life support"],
    "Mail Label Fraud": ["mail label", "mlm", "iphone return", "imei", "return fraud"],
    "Mental Health & Wellbeing Group": ["mental health", "wellbeing", "mhw"],
    "Arcelik Foundation": ["arçelik", "arcelik", "romania", "paintshop", "total teknik"],
}

# ---------- canonicalisation applied at ingest, so retrieval cannot surface a ruled-out claim ----------
EXCLUDED_CLAIMS = [  # paragraphs matching these are dropped from the index (the artifact's CS10 exclusion)
    r"ACES AI Strategy", r"Hoshin Kanri", r"AI strategy authorship", r"authored (?:a|the) (?:formal|company-level|org-level)? ?AI strategy",
    r"org-level AI strategy I authored", r"company-level Agentic AI strategy",
]
CANONICAL_REPLACEMENTS = [  # (pattern, replacement): where the canonical record overrides a source document
    (r"VP WW Global Programs?", "Worldwide Programme Lead"),
    (r"Worldwide VP-level programme", "Worldwide programme"),
    (r"MHW VP Expansion", "MHW Worldwide Expansion"),
    (r"Global Programme VP Delivery", "Global Programme Delivery"),
    (r"grew to VP WW Global", "grew to a Worldwide programme"),
]
LEVEL_CODES = r"\b(?:Amazon )?L[4-7](?:\s?(?:to|/|-|→)\s?L?[4-7])?(?:\s?STL)?\b"  # stripped from generated text

# ---------- LinkedIn launcher (artifact) ----------
COMPANIES = {  # name -> verified LinkedIn company id (None = keyword search)
    "Google": "1441", "Deloitte": "1038", "Nvidia": "3608", "Zalando": "69267561", "BSH Hausgeräte": "6594",
    "Siemens AG": "1043", "Bosch": "2508619", "Sony": "57993393", "Microsoft": "1035", "N26": "3116425",
    "HelloFresh": "2454643", "Delivery Hero": "2569398", "Deutsche Bahn": "4823", "SAP": "1115", "Temu": "90534028",
    "Accenture": "15144555", "Wolt": "3995846", "Samsung": "85881048", "Meta": "10667", "Uber": None,
    "Viatris": None, "Novartis": None, "Hitachi Energy": None, "AXA": None, "BeiGene": None,
}
TIERS = {
    "t1": ["Google", "Nvidia", "Microsoft", "Meta"],
    "t2": ["Zalando", "HelloFresh", "Wolt", "N26", "Delivery Hero", "Uber"],
    "t3": ["Bosch", "BSH Hausgeräte", "Deutsche Bahn", "Sony", "Siemens AG", "Samsung", "Accenture", "SAP", "Temu", "Deloitte"],
    "t4": ["Viatris", "Novartis", "Hitachi Energy", "AXA", "BeiGene"],
}
TIER_LABEL = {"t1": "Tier 1", "t2": "Tier 2", "t3": "Tier 3", "t4": "Expansion", "other": "Other"}
SEARCH_TERMS = ('("Continuous Improvement" OR "Process Excellence" OR "Lean Six Sigma" OR "Operational Excellence" '
                'OR "AI Strategy" OR "Digital Transformation") AND ("Head of" OR "Senior Manager" OR Director OR '
                'Principal OR Lead OR Expert) NOT "Software Engineer" NOT "Account Executive" NOT "Sales Representative"')
RECENCY = {"Last week": "r604800", "Last 2 weeks": "r1209600", "Last 4 weeks": "r2419200",
           "Last 3 months": "r7776000", "Last 6 months": "r15552000"}

# ---------- pipeline taxonomy (artifact) ----------
STAGES = [("notapplied", "Not applied yet"), ("applied", "Applied"), ("screen", "Recruiter screen"),
          ("hm", "Hiring manager"), ("task", "Assignment / case"), ("panel", "Panel / final"), ("offer", "Offer")]
TERMINAL = [("rejected", "Rejected"), ("withdrawn", "Withdrawn")]
SUBSTATUS = {
    "new": [("researching", "Researching"), ("notready", "Not ready to apply"),
            ("creatingdocs", "Creating documents"), ("ready", "Ready to apply")],
    "saved": STAGES + TERMINAL,
    "dismissed": [("lang", "Language"), ("score", "Score"), ("skillgap", "Skill gap"), ("other", "Other")],
}
SUBSTATUS_LABEL = {k: v for opts in SUBSTATUS.values() for k, v in opts}
LEVEL_LABEL = {"below": "Below target", "senior-mgr": "Senior Manager", "head": "Head of", "director": "Director",
               "senior-ic": "Senior IC / Principal", "vp": "VP and above", "unclear": "Unclear"}
