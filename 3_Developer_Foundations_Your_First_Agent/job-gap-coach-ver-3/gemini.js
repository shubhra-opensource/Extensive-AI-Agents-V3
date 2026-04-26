const GEMINI_MODEL = "gemini-3-flash-preview";
const GEMINI_URL = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent`;

function formatLogSection(title, value) {
  return `## ${title}\n${value == null ? "" : String(value)}\n`;
}

async function saveLlmCallLog(entry) {
  try {
    if (!chrome?.downloads?.download) return;

    const ts = new Date().toISOString();
    const safeType = String(entry.callType || "unknown").replace(/[^a-z0-9_-]/gi, "_");
    const filename = `job-gap-coach-logs/${ts.replace(/[:.]/g, "-")}-${safeType}.log`;

    const sections = [
      formatLogSection("timestamp", ts),
      formatLogSection("callType", entry.callType || "unknown"),
      formatLogSection("model", GEMINI_MODEL),
      formatLogSection("status", entry.status || "unknown"),
      formatLogSection("httpStatus", entry.httpStatus || "n/a"),
      formatLogSection("finishReason", entry.finishReason || "n/a"),
      formatLogSection("error", entry.error || "n/a"),
      formatLogSection("prompt", entry.prompt || ""),
      formatLogSection("response", entry.response || "")
    ];

    const content = `${sections.join("\n")}\n`;
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);

    try {
      await chrome.downloads.download({
        url,
        filename,
        saveAs: false,
        conflictAction: "uniquify"
      });
    } finally {
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  } catch (err) {
    console.warn("Could not save LLM call log:", err);
  }
}

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

const SIMILAR_JOBS_JSON_INSTRUCTION = `You are a technical career coach.
Given the candidate's resume and the current job posting, suggest close-match roles the candidate can realistically apply to now.
Return ONLY valid JSON (no markdown) with this exact shape:
{
  "similarJobs": [
    {
      "title": string,
      "reason": string,
      "searchQuery": string
    }
  ]
}
Rules:
- Return 5 to 8 jobs.
- Keep titles concrete and searchable (for example: "Backend Engineer (Node.js, AWS)").
- reason should be one short sentence explaining why this role is similar.
- searchQuery should be optimized for job boards and include the role plus key stack terms.
- Do not include fields outside this schema.`;

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
  try {
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
      await saveLlmCallLog({
        callType: "job-gap-analysis",
        status: "error",
        httpStatus: res.status,
        error: msg,
        prompt: userBlock,
        response: JSON.stringify(data, null, 2)
      });
      throw new Error(msg);
    }

    const partText =
      data?.candidates?.[0]?.content?.parts?.map((p) => p.text || "").join("") || "";
    const finish = data?.candidates?.[0]?.finishReason;
    if (finish && finish !== "STOP") {
      const finishMessage = `Gemini finished with ${finish}. Try again or shorten the job text.`;
      await saveLlmCallLog({
        callType: "job-gap-analysis",
        status: "error",
        httpStatus: res.status,
        finishReason: finish,
        error: finishMessage,
        prompt: userBlock,
        response: partText
      });
      throw new Error(finishMessage);
    }

    let parsed;
    try {
      parsed = JSON.parse(stripJsonFence(partText));
    } catch {
      const parseMessage = "Could not parse Gemini JSON. Try again.";
      await saveLlmCallLog({
        callType: "job-gap-analysis",
        status: "error",
        httpStatus: res.status,
        finishReason: finish,
        error: parseMessage,
        prompt: userBlock,
        response: partText
      });
      throw new Error(parseMessage);
    }

    const normalized = normalizeAnalysis(parsed);
    await saveLlmCallLog({
      callType: "job-gap-analysis",
      status: "success",
      httpStatus: res.status,
      finishReason: finish,
      prompt: userBlock,
      response: partText
    });
    return normalized;
  } catch (err) {
    if (err instanceof Error && err.message === "Failed to fetch") {
      await saveLlmCallLog({
        callType: "job-gap-analysis",
        status: "error",
        error: err.message,
        prompt: userBlock
      });
    }
    throw err;
  }
}

function normalizeSimilarJobs(raw) {
  const similarJobs = Array.isArray(raw?.similarJobs) ? raw.similarJobs : [];

  return similarJobs
    .map((job) => ({
      title: String(job?.title || "").trim(),
      reason: String(job?.reason || "").trim(),
      searchQuery: String(job?.searchQuery || "").trim()
    }))
    .filter((job) => job.title && job.searchQuery)
    .slice(0, 8);
}

async function suggestSimilarJobsWithGemini(apiKey, resumeText, jobPayload) {
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
    SIMILAR_JOBS_JSON_INSTRUCTION,
    "",
    "=== RESUME / SKILLS ===",
    resumeText.slice(0, 32000),
    "",
    "=== CURRENT JOB ===",
    jobBody
  ].join("\n");

  const url = `${GEMINI_URL}?key=${encodeURIComponent(apiKey.trim())}`;
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ role: "user", parts: [{ text: userBlock }] }],
        generationConfig: {
          temperature: 0.7,
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
      await saveLlmCallLog({
        callType: "similar-jobs",
        status: "error",
        httpStatus: res.status,
        error: msg,
        prompt: userBlock,
        response: JSON.stringify(data, null, 2)
      });
      throw new Error(msg);
    }

    const partText =
      data?.candidates?.[0]?.content?.parts?.map((p) => p.text || "").join("") || "";
    const finish = data?.candidates?.[0]?.finishReason;
    if (finish && finish !== "STOP") {
      const finishMessage = `Gemini finished with ${finish}. Try again or shorten the job text.`;
      await saveLlmCallLog({
        callType: "similar-jobs",
        status: "error",
        httpStatus: res.status,
        finishReason: finish,
        error: finishMessage,
        prompt: userBlock,
        response: partText
      });
      throw new Error(finishMessage);
    }

    let parsed;
    try {
      parsed = JSON.parse(stripJsonFence(partText));
    } catch {
      const parseMessage = "Could not parse Gemini JSON for similar jobs. Try again.";
      await saveLlmCallLog({
        callType: "similar-jobs",
        status: "error",
        httpStatus: res.status,
        finishReason: finish,
        error: parseMessage,
        prompt: userBlock,
        response: partText
      });
      throw new Error(parseMessage);
    }

    const normalized = normalizeSimilarJobs(parsed);
    if (!normalized.length) {
      const emptyMessage = "Gemini did not return similar jobs. Try again.";
      await saveLlmCallLog({
        callType: "similar-jobs",
        status: "error",
        httpStatus: res.status,
        finishReason: finish,
        error: emptyMessage,
        prompt: userBlock,
        response: partText
      });
      throw new Error(emptyMessage);
    }

    await saveLlmCallLog({
      callType: "similar-jobs",
      status: "success",
      httpStatus: res.status,
      finishReason: finish,
      prompt: userBlock,
      response: partText
    });
    return normalized;
  } catch (err) {
    if (err instanceof Error && err.message === "Failed to fetch") {
      await saveLlmCallLog({
        callType: "similar-jobs",
        status: "error",
        error: err.message,
        prompt: userBlock
      });
    }
    throw err;
  }
}
