const GEMINI_MODEL = "gemini-3-flash-preview";
const GEMINI_URL = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent`;

const ANALYSIS_JSON_INSTRUCTION = `You are a career coach. Compare the candidate's resume/skills text with the job posting.
Return ONLY valid JSON (no markdown) with this exact shape:
{
  "matched": [ { "skill": string, "category": string, "count": number } ],
  "missing": [ { "skill": string, "category": string, "count": number, "priority": "Must Learn" | "Nice to Have" | "Ignore for Now" } ],
  "groupedMissing": { "<category_name>": [ "skill1", "skill2" ] },
  "roadmap": [ { "week": "Week 1", "focus": string }, { "week": "Week 2", "focus": string }, { "week": "Week 3", "focus": string }, { "week": "Week 4", "focus": string } ]
}
Rules:
- Extract concrete technical skills, tools, frameworks, clouds, and methods mentioned in the job that matter for the role.
- "count" = approximate emphasis in the job text (1 if mentioned once or lightly, 2 if clearly important, 3+ if central/repeated).
- "priority" for missing: use counts — 3+ => Must Learn, 2 => Nice to Have, 1 => Ignore for Now.
- matched: skills that clearly appear in BOTH resume and job (normalize names, e.g. "K8s" vs "kubernetes").
- groupedMissing: group missing skills by sensible categories (languages, data, ml_ai, cloud, infra, other).
- roadmap: four weekly focus strings tailored to the top missing skills.
- Use empty arrays/objects only if nothing applies.`;

function stripJsonFence(text) {
  const t = (text || "").trim();
  const fence = /^```(?:json)?\s*([\s\S]*?)\s*```$/i.exec(t);
  return fence ? fence[1].trim() : t;
}

function normalizeAnalysis(raw) {
  const matched = Array.isArray(raw.matched) ? raw.matched : [];
  const missing = Array.isArray(raw.missing) ? raw.missing : [];
  const groupedMissing =
    raw.groupedMissing && typeof raw.groupedMissing === "object" && !Array.isArray(raw.groupedMissing)
      ? raw.groupedMissing
      : {};
  const roadmap = Array.isArray(raw.roadmap) ? raw.roadmap : [];

  return {
    resumeSkills: [],
    jobSkills: [],
    matched: matched.map((m) => ({
      skill: String(m.skill || ""),
      category: m.category != null ? String(m.category) : "other",
      count: Number(m.count) || 1
    })).filter((m) => m.skill),
    missing: missing
      .map((m) => ({
        skill: String(m.skill || ""),
        category: m.category != null ? String(m.category) : "other",
        count: Number(m.count) || 1,
        priority: ["Must Learn", "Nice to Have", "Ignore for Now"].includes(m.priority)
          ? m.priority
          : "Ignore for Now"
      }))
      .filter((m) => m.skill)
      .sort((a, b) => b.count - a.count || a.skill.localeCompare(b.skill)),
    groupedMissing,
    roadmap: roadmap
      .map((r) => ({
        week: String(r.week || ""),
        focus: String(r.focus || "")
      }))
      .filter((r) => r.week && r.focus)
  };
}

async function analyzeJobGapWithGemini(apiKey, resumeText, jobPayload) {
  if (!apiKey || !apiKey.trim()) {
    throw new Error("Missing Gemini API key.");
  }

  const jobBody = [
    `Job title: ${jobPayload.title || "N/A"}`,
    `Company: ${jobPayload.company || "N/A"}`,
    `URL: ${jobPayload.url || "N/A"}`,
    "",
    "Job description:",
    (jobPayload.description || "").slice(0, 48000)
  ].join("\n");

  const userBlock = [
    ANALYSIS_JSON_INSTRUCTION,
    "",
    "=== RESUME / SKILLS ===",
    resumeText.slice(0, 32000),
    "",
    "=== JOB ===",
    jobBody
  ].join("\n");

  const url = `${GEMINI_URL}?key=${encodeURIComponent(apiKey.trim())}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contents: [{ role: "user", parts: [{ text: userBlock }] }],
      generationConfig: {
        temperature: 1,
        responseMimeType: "application/json"
      }
    })
  });

  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const msg =
      data?.error?.message ||
      data?.error?.status ||
      `Gemini request failed (${res.status})`;
    throw new Error(msg);
  }

  const partText =
    data?.candidates?.[0]?.content?.parts?.map((p) => p.text || "").join("") || "";
  const finish = data?.candidates?.[0]?.finishReason;
  if (finish && finish !== "STOP") {
    throw new Error(`Gemini finished with ${finish}. Try again or shorten the job text.`);
  }

  let parsed;
  try {
    parsed = JSON.parse(stripJsonFence(partText));
  } catch {
    throw new Error("Could not parse Gemini JSON. Try again.");
  }

  return normalizeAnalysis(parsed);
}
