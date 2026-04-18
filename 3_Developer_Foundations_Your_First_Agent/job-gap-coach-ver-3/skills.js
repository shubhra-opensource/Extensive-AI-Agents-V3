const SKILL_DICTIONARY = {
    languages: [
      "python", "sql", "java", "javascript", "typescript", "scala", "r", "c++"
    ],
    data: [
      "pandas", "numpy", "spark", "hadoop", "etl", "data modeling", "data analysis"
    ],
    ml_ai: [
      "machine learning", "deep learning", "tensorflow", "pytorch",
      "scikit-learn", "nlp", "llm", "rag", "langchain"
    ],
    infra: [
      "docker", "kubernetes", "airflow", "git", "ci/cd", "jenkins",
      "github actions", "system design", "linux", "api", "rest api"
    ],
    cloud: [
      "aws", "gcp", "azure"
    ]
  };
  
  function normalizeText(text) {
    return (text || "").toLowerCase();
  }
  
  function countOccurrences(text, phrase) {
    const escaped = phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const matches = text.match(new RegExp(escaped, "gi"));
    return matches ? matches.length : 0;
  }
  
  function getSkillCategory(skill) {
    for (const category of Object.keys(SKILL_DICTIONARY)) {
      if (SKILL_DICTIONARY[category].includes(skill)) {
        return category;
      }
    }
    return "other";
  }
  
  function extractSkillsWithMeta(text) {
    const normalized = normalizeText(text);
    const found = [];
  
    for (const category of Object.keys(SKILL_DICTIONARY)) {
      for (const skill of SKILL_DICTIONARY[category]) {
        const count = countOccurrences(normalized, skill.toLowerCase());
        if (count > 0) {
          found.push({
            skill,
            category,
            count
          });
        }
      }
    }
  
    return found.sort((a, b) => b.count - a.count || a.skill.localeCompare(b.skill));
  }
  
  function getPriorityLabel(count) {
    if (count >= 3) return "Must Learn";
    if (count === 2) return "Nice to Have";
    return "Ignore for Now";
  }
  
  function groupByCategory(skills) {
    const grouped = {};
  
    skills.forEach(item => {
      if (!grouped[item.category]) grouped[item.category] = [];
      grouped[item.category].push(item.skill);
    });
  
    return grouped;
  }
  
  function buildRoadmap(missingSkills) {
    const topSkills = missingSkills.slice(0, 4).map(item => item.skill);
  
    const week1 = topSkills.slice(0, 1);
    const week2 = topSkills.slice(1, 2);
    const week3 = topSkills.slice(2, 3);
    const week4 = topSkills.slice(3, 4);
  
    return [
      {
        week: "Week 1",
        focus: week1.length ? `Learn the basics of ${week1.join(", ")}` : "Review your strongest matched skills"
      },
      {
        week: "Week 2",
        focus: week2.length ? `Build one small project using ${week2.join(", ")}` : "Improve resume examples"
      },
      {
        week: "Week 3",
        focus: week3.length ? `Practice interview questions on ${week3.join(", ")}` : "Revise technical foundations"
      },
      {
        week: "Week 4",
        focus: week4.length ? `Combine and revise ${week4.join(", ")}` : "Do mock interviews and polish resume"
      }
    ];
  }
  
  function compareSkills(resumeText, jobText) {
    const resumeSkillsMeta = extractSkillsWithMeta(resumeText);
    const jobSkillsMeta = extractSkillsWithMeta(jobText);
  
    const resumeSkillSet = new Set(resumeSkillsMeta.map(item => item.skill));
  
    const matched = jobSkillsMeta.filter(item => resumeSkillSet.has(item.skill));
    const missing = jobSkillsMeta
      .filter(item => !resumeSkillSet.has(item.skill))
      .map(item => ({
        ...item,
        priority: getPriorityLabel(item.count)
      }))
      .sort((a, b) => b.count - a.count || a.skill.localeCompare(b.skill));
  
    return {
      resumeSkills: resumeSkillsMeta,
      jobSkills: jobSkillsMeta,
      matched,
      missing,
      groupedMissing: groupByCategory(missing),
      roadmap: buildRoadmap(missing)
    };
  }