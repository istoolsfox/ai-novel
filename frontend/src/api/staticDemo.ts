// ===== Static demo API：用于 Netlify 纯静态演示 =====
// 这个模块只在 VITE_STATIC_DEMO=true 时启用。它把原本需要 FastAPI 的接口
// 改成本地 localStorage 数据，方便直接部署到 Netlify 给别人看完整页面流程。

const STORAGE_KEY = "ai_novel_static_demo_v1";
const STEPS = [
  "brief",
  "seed",
  "draft",
  "dialogue",
  "archaeology",
  "reader_pull",
  "deepen",
  "anti_ai",
  "finalize",
];

type Db = {
  projects: any[];
  chapters: Record<string, any[]>;
  blueprints: Record<string, any[]>;
  jobs: Record<string, any[]>;
  steps: Record<string, any[]>;
  resources: Record<string, Record<string, any[]>>;
  versions: Record<string, any[]>;
  quality: Record<string, any[]>;
};

export function isStaticDemoEnabled(): boolean {
  return import.meta.env.VITE_STATIC_DEMO === "true";
}

function now() {
  return new Date().toISOString();
}

function id(prefix: string) {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}

function wordCount(text: string) {
  return (text || "").replace(/\s+/g, "").length;
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value));
}

function resource(projectId: string, title: string, category: string, content: string, payload: Record<string, any>) {
  return {
    id: id("rec"),
    project_id: projectId,
    title,
    category,
    content,
    payload,
    status: payload.status || "active",
    created_at: now(),
    updated_at: now(),
  };
}

function chapter(projectId: string, n: number, title: string, draft: string) {
  return {
    id: `ch-${n}`,
    project_id: projectId,
    outline_id: `outline-${n}`,
    chapter_number: n,
    title,
    brief: `第 ${n} 章概要：推进主线冲突，同时保留下一章钩子。`,
    draft,
    summary: `第 ${n} 章完成关键推进，并留下承接点。`,
    word_count: wordCount(draft),
    status: "finalized",
    selected_version_id: `ver-${n}`,
    quality_score: 86 + n,
    created_at: now(),
    updated_at: now(),
  };
}

function demoDraft(n: number, title: string) {
  return `# 第 ${n} 章 ${title}\n\n雨停在旧城区的玻璃天桥上，林晚把录音笔贴近掌心。屏幕里那一行未命名文件像一枚细小的刺，提醒她三年前的事故并没有真正结束。\n\n周砚没有催她。他只是把办公室的灯调暗，让窗外的霓虹在桌面上流成一条冷色的河。\n\n“如果你现在打开它，”他说，“你听到的可能不是证据，而是另一个人留给你的求救。”\n\n林晚笑了一下，却没有声音。她终于按下播放键。电流噪声之后，一个熟悉到不该出现的声音，在房间里轻轻说出了她的名字。\n\n章节衔接：下一章必须承接录音内容，不要跳过林晚的即时反应。`;
}

function seedDb(): Db {
  const projectId = "demo-project";
  const projects = [
    {
      id: projectId,
      title: "雾港回声",
      topic: "失踪案、记忆与城市秘密",
      genre: "都市悬疑",
      audience: "青年读者",
      tone: "冷灰、克制、情绪暗涌",
      target_chapter_count: 20,
      target_words_per_chapter: 3000,
      logline: "一名调查记者追查三年前失踪案，却发现每条线索都指向她被篡改的记忆。",
      synopsis: "故事发生在常年潮湿的雾港。林晚收到一段匿名录音后，重新调查三年前被结案的失踪案，并在关系网、旧档案和自身记忆裂缝中逼近真相。",
      global_summary: "主线围绕失踪案、录音、旧城改造与记忆错位展开。",
      status: "active",
      privacy_mode: 1,
      project_root_path: "static-demo://ai-novel/demo-project",
      created_at: now(),
      updated_at: now(),
    },
  ];

  const chapters = {
    [projectId]: [
      chapter(projectId, 1, "匿名录音", demoDraft(1, "匿名录音")),
      chapter(projectId, 2, "旧楼里的名单", demoDraft(2, "旧楼里的名单")),
      chapter(projectId, 3, "天桥尽头的人", demoDraft(3, "天桥尽头的人")),
    ],
  };

  const blueprints = {
    [projectId]: [
      {
        id: "bp-demo",
        project_id: projectId,
        volume_number: 1,
        volume_title: "雾港旧声",
        volume_arc: "主角接收匿名录音，追查旧案，逐步发现失踪者与自己记忆之间的关系。",
        chapter_range: { start: 1, end: 10 },
        emotional_climate: { tone: "克制、压抑、逐步升温", motif: "雨、录音、电流声" },
        key_foreshadowings: ["录音中的第二个呼吸声", "旧城区门牌号 17"],
        character_arcs: ["林晚从旁观调查者变成事件核心当事人"],
        recurring_motifs: ["雨声", "蓝色霓虹", "空白磁带"],
        taboo_list: ["不要突然跳过调查过程", "不要用旁白直接解释全部真相"],
        generation_params: { memory_mode: "local-static-demo", chapter_bridge_required: true },
        status: "approved",
        created_at: now(),
        updated_at: now(),
      },
    ],
  };

  const resources: Db["resources"] = {
    [projectId]: {
      outlines: [
        resource(projectId, "第1章 匿名录音", "chapter_outline", "林晚收到匿名录音，决定重启调查。", {
          chapter_number: "1",
          volume: "雾港旧声",
          chapter_title: "匿名录音",
          chapter_goal: "建立悬疑钩子，展示主角职业和情绪压抑。",
          main_conflict: "是否打开录音，以及录音是否会推翻旧案结论。",
          key_events: "收到录音；联系周砚；听到失踪者声音。",
          emotional_rhythm: "冷静压抑 → 犹豫 → 震动",
          hook: "录音里有人叫出林晚的名字。",
          completion_status: "completed",
        }),
        resource(projectId, "第2章 旧楼里的名单", "chapter_outline", "主角进入旧楼，发现旧案名单。", {
          chapter_number: "2",
          volume: "雾港旧声",
          chapter_title: "旧楼里的名单",
          chapter_goal: "扩大线索网络。",
          main_conflict: "名单是否可信。",
          key_events: "旧楼调查；找到门牌号17；遭遇尾随。",
          emotional_rhythm: "紧张 → 逼近 → 被迫撤离",
          hook: "名单最后一栏写着林晚的名字。",
          completion_status: "active",
        }),
      ],
      "character-profiles": [
        resource(projectId, "林晚", "主角", "调查记者，冷静克制，害怕自己的记忆不可靠。", {
          name: "林晚",
          role: "主角 / 调查记者",
          faction: "雾港晚报",
          traits: "克制、敏锐、抗拒脆弱",
          desire: "查清三年前失踪案真相",
          fear: "发现自己也是谎言的一部分",
          arc: "从旁观调查者变成主动面对记忆裂缝的人",
        }),
        resource(projectId, "周砚", "盟友", "档案修复师，熟悉旧城资料，隐瞒了与失踪案的关联。", {
          name: "周砚",
          role: "盟友 / 档案修复师",
          faction: "旧城档案馆",
          traits: "温和、谨慎、说话留白",
          desire: "保护林晚，也保护一段不能公开的旧档案",
          fear: "真相公开后失去最后的信任",
          arc: "从协助者变成必须被质疑的人",
        }),
      ],
      "character-relationships": [
        resource(projectId, "林晚 → 周砚", "隐秘同盟", "互相信任但信息不对等。", {
          source_character: "林晚",
          target_character: "周砚",
          relationship_type: "隐秘同盟",
          strength: 7,
          conflict: "周砚知道旧案细节却不愿全部说明。",
          change_history: "第1章合作，第3章开始出现信任裂痕。",
        }),
      ],
      "timeline-events": [
        resource(projectId, "三年前的失踪案", "timeline", "雾港旧城改造前夜，关键证人失踪。", {
          event_time: "三年前雨季",
          chapter: "背景事件",
          characters: "林晚、周砚、失踪者",
          cause: "旧城档案被人调换。",
          consequence: "案件被草草结案。",
          status: "已确认",
        }),
      ],
      foreshadowings: [
        resource(projectId, "录音里的第二个呼吸声", "open", "录音里除失踪者外还有第二个人。", {
          setup_chapter: "1",
          payoff_chapter: "6",
          status: "planted",
          related_characters: "林晚、周砚",
          hint: "第二个呼吸声节奏与周砚的旧病相似。",
          payoff_plan: "第6章让林晚通过医院记录发现线索。",
        }),
      ],
      "style-profiles": [
        resource(projectId, "冷灰悬疑风格", "style", "短句克制，画面冷色，情绪放在动作和物件里。", {
          title: "冷灰悬疑风格",
          sample: "雨水从霓虹灯牌下落下来。她没有抬头，只把录音笔握得更紧。",
          analysis: "少解释，多动作；环境承担情绪；对白保留潜台词。",
          writing_goal: "都市悬疑、现实主义、情绪暗涌",
        }),
      ],
      "taboo-rules": [
        resource(projectId, "不要直接揭示真相", "medium", "悬疑信息必须分阶段释放。", {
          rule: "不要用旁白一次性解释旧案真相。",
          severity: "medium",
          scope: "全书",
          response: "通过证据、对话和行动递进揭示。",
        }),
      ],
      "knowledge-documents": [
        resource(projectId, "雾港城市设定", "reference", "港口、旧城、档案馆、连年雨季构成故事底色。", {
          wiki_path: "world/雾港.md",
          source_type: "worldbuilding",
          tags: "城市,旧城,档案馆",
          content: "雾港是一座潮湿的海港城市，旧城区正在被改造，许多旧档案在搬迁中遗失。",
        }),
      ],
    },
  };

  const jobs = {
    [projectId]: [
      {
        id: "job-demo",
        project_id: projectId,
        blueprint_id: "bp-demo",
        start_chapter: 1,
        start_chapter_number: 1,
        target_chapter_count: 3,
        current_chapter_number: 3,
        completed_chapter_count: 3,
        progress_percent: 100,
        current_step: "finalize",
        status: "completed",
        checkpoint_strategy: "none",
        auto_finalize: true,
        params: { hosting_mode: "pure", generation_mode: "standard" },
        error_message: "",
        created_at: now(),
        updated_at: now(),
      },
    ],
  };

  const steps = { ["job-demo"]: buildSteps(projectId, "job-demo", 1, 3) };
  const versions = { "ch-1": [], "ch-2": [], "ch-3": [] };
  const quality = { "ch-1": [], "ch-2": [], "ch-3": [] };

  return { projects, chapters, blueprints, jobs, steps, resources, versions, quality };
}

function buildSteps(projectId: string, jobId: string, start: number, count: number) {
  const rows: any[] = [];
  for (let n = start; n < start + count; n += 1) {
    for (const step of STEPS) {
      rows.push({
        id: id("step"),
        job_id: jobId,
        project_id: projectId,
        chapter_id: `ch-${n}`,
        chapter_number: n,
        step_name: step,
        step_status: "completed",
        status: "done",
        step_output: `${step} 已完成（静态演示数据）`,
        output_text: `${step} 已完成（静态演示数据）`,
        error_message: "",
        duration_ms: 120,
        started_at: now(),
        completed_at: now(),
        created_at: now(),
      });
    }
  }
  return rows;
}

function loadDb(): Db {
  if (typeof window === "undefined") return seedDb();
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    const seeded = seedDb();
    saveDb(seeded);
    return seeded;
  }
  try {
    return JSON.parse(raw) as Db;
  } catch {
    const seeded = seedDb();
    saveDb(seeded);
    return seeded;
  }
}

function saveDb(db: Db) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
  }
}

function ensureProjectBuckets(db: Db, projectId: string) {
  db.chapters[projectId] ||= [];
  db.blueprints[projectId] ||= [];
  db.jobs[projectId] ||= [];
  db.resources[projectId] ||= {};
}

function findProject(db: Db, projectId: string) {
  const project = db.projects.find((p) => p.id === projectId);
  if (!project) throw new Error(`静态演示中找不到项目 ${projectId}`);
  return project;
}

function parse(path: string) {
  const [clean, query = ""] = path.split("?");
  return { clean, query: new URLSearchParams(query) };
}

function createBlueprint(db: Db, projectId: string, body: any = {}) {
  const bp = {
    id: id("bp"),
    project_id: projectId,
    volume_number: body.volume_number || 1,
    volume_title: body.volume_title || "自动生成卷蓝图",
    volume_arc: body.volume_arc || "静态演示：系统自动生成卷主线、情绪曲线和章节范围。",
    chapter_range: body.chapter_range || { start: 1, end: 10 },
    emotional_climate: body.emotional_climate || { tone: "递进式悬疑", pressure: "逐章加深" },
    key_foreshadowings: body.key_foreshadowings || ["匿名录音", "旧城门牌"],
    character_arcs: body.character_arcs || ["主角逐步逼近自己的记忆裂缝"],
    recurring_motifs: body.recurring_motifs || ["雨声", "录音", "霓虹"],
    taboo_list: body.taboo_list || ["不要突然揭底", "不要跳过情绪承接"],
    generation_params: body.generation_params || { memory_mode: "static-demo" },
    status: body.status || "approved",
    created_at: now(),
    updated_at: now(),
  };
  db.blueprints[projectId].unshift(bp);
  return bp;
}

function ensureDemoAssets(db: Db, projectId: string) {
  ensureProjectBuckets(db, projectId);
  const resources = db.resources[projectId];
  resources.outlines ||= [];
  resources["character-profiles"] ||= [];
  resources["character-relationships"] ||= [];
  if (resources.outlines.length === 0) {
    resources.outlines.push(
      resource(projectId, "第1章 自动大纲", "chapter_outline", "静态演示自动补齐的大纲。", {
        chapter_number: "1",
        chapter_title: "自动大纲",
        chapter_goal: "展示托管链路会先准备大纲。",
        main_conflict: "主角收到异常线索。",
        emotional_rhythm: "疑惑 → 紧张 → 被迫行动",
        completion_status: "active",
      }),
    );
  }
  if (resources["character-profiles"].length === 0) {
    resources["character-profiles"].push(
      resource(projectId, "主角", "character", "自动生成的主角档案。", {
        name: "主角",
        role: "核心视角人物",
        traits: "敏锐、压抑、执拗",
        desire: "追查真相",
      }),
    );
  }
  if (resources["character-relationships"].length === 0) {
    resources["character-relationships"].push(
      resource(projectId, "主角 → 盟友", "关系", "静态演示关系记录。", {
        source_character: "主角",
        target_character: "盟友",
        relationship_type: "同盟",
        strength: 6,
      }),
    );
  }
}

function createChaptersForJob(db: Db, projectId: string, start: number, count: number) {
  const list = db.chapters[projectId];
  const created: any[] = [];
  for (let n = start; n < start + count; n += 1) {
    let row = list.find((ch) => ch.chapter_number === n);
    if (!row) {
      row = chapter(projectId, n, `静态演示第 ${n} 章`, demoDraft(n, `静态演示第 ${n} 章`));
      list.push(row);
    }
    created.push(row);
  }
  list.sort((a, b) => a.chapter_number - b.chapter_number);
  return created;
}

function startJob(db: Db, projectId: string, body: any = {}) {
  ensureProjectBuckets(db, projectId);
  const start = Number(body.start_chapter || 1);
  const count = Number(body.count || body.target_chapter_count || 3);
  if (!body.blueprint_id && db.blueprints[projectId].length === 0) createBlueprint(db, projectId);
  createChaptersForJob(db, projectId, start, count);
  const job = {
    id: id("job"),
    project_id: projectId,
    blueprint_id: body.blueprint_id || db.blueprints[projectId][0]?.id,
    start_chapter: start,
    start_chapter_number: start,
    target_chapter_count: count,
    current_chapter_number: start,
    completed_chapter_count: 0,
    progress_percent: 0,
    current_step: "brief",
    status: "running",
    checkpoint_strategy: body.checkpoint_strategy || "none",
    auto_finalize: body.auto_finalize ?? true,
    params: body.params || {},
    error_message: "",
    created_at: now(),
    updated_at: now(),
  };
  db.jobs[projectId].unshift(job);
  db.steps[job.id] = buildSteps(projectId, job.id, start, count);
  return job;
}

function completeJob(jobId: string) {
  const db = loadDb();
  for (const jobs of Object.values(db.jobs)) {
    const job = jobs.find((j) => j.id === jobId);
    if (job) {
      job.status = "completed";
      job.completed_chapter_count = job.target_chapter_count;
      job.progress_percent = 100;
      job.current_step = "finalize";
      job.updated_at = now();
      saveDb(db);
      return;
    }
  }
}

function buildNovelMarkdown(db: Db, projectId: string) {
  const project = findProject(db, projectId);
  const chapters = db.chapters[projectId] || [];
  return `# ${project.title}\n\n${project.synopsis || project.logline || ""}\n\n${chapters
    .map((ch) => `## 第 ${ch.chapter_number} 章 ${ch.title}\n\n${ch.draft || ch.summary || ""}`)
    .join("\n\n")}`;
}

export async function staticRequest<T>(method: string, path: string, body?: any): Promise<T> {
  const db = loadDb();
  const { clean, query } = parse(path);

  if (clean === "/api/auth/status") {
    return { mode: "static-demo", authenticated: true, user: null, sync_enabled: false, message: "Netlify 静态演示模式" } as T;
  }
  if (clean === "/api/auth/logout") return { ok: true } as T;

  if (clean === "/api/projects") {
    if (method === "GET") return clone(db.projects) as T;
    if (method === "POST") {
      const project = {
        id: id("project"),
        title: body?.title || "未命名项目",
        topic: body?.topic || "",
        genre: body?.genre || "",
        audience: body?.audience || "",
        tone: body?.tone || "",
        target_chapter_count: body?.target_chapter_count || 20,
        target_words_per_chapter: body?.target_words_per_chapter || 3000,
        logline: body?.logline || "",
        synopsis: body?.synopsis || "",
        global_summary: body?.global_summary || "",
        status: "active",
        privacy_mode: body?.privacy_mode === false ? 0 : 1,
        project_root_path: "static-demo://custom-project",
        created_at: now(),
        updated_at: now(),
      };
      db.projects.unshift(project);
      ensureProjectBuckets(db, project.id);
      createBlueprint(db, project.id, { volume_title: "演示卷蓝图" });
      saveDb(db);
      return clone(project) as T;
    }
  }

  let match = clean.match(/^\/api\/projects\/([^/]+)$/);
  if (match) {
    const projectId = match[1];
    const project = findProject(db, projectId);
    if (method === "GET") return clone(project) as T;
    if (method === "PATCH") {
      Object.assign(project, body || {}, { updated_at: now(), privacy_mode: body?.privacy_mode === false ? 0 : 1 });
      saveDb(db);
      return clone(project) as T;
    }
    if (method === "DELETE") {
      db.projects = db.projects.filter((p) => p.id !== projectId);
      delete db.chapters[projectId];
      delete db.blueprints[projectId];
      delete db.jobs[projectId];
      delete db.resources[projectId];
      saveDb(db);
      return { ok: true } as T;
    }
  }

  match = clean.match(/^\/api\/projects\/([^/]+)\/chapters$/);
  if (match) {
    const projectId = match[1];
    ensureProjectBuckets(db, projectId);
    if (method === "GET") return clone(db.chapters[projectId].sort((a, b) => a.chapter_number - b.chapter_number)) as T;
    if (method === "POST") {
      const n = body?.chapter_number || db.chapters[projectId].length + 1;
      const row = chapter(projectId, n, body?.title || `第 ${n} 章`, body?.draft || "");
      Object.assign(row, body || {}, { word_count: wordCount(body?.draft || ""), updated_at: now() });
      db.chapters[projectId].push(row);
      saveDb(db);
      return clone(row) as T;
    }
  }

  match = clean.match(/^\/api\/projects\/([^/]+)\/chapters\/([^/]+)\/(quality-scores|versions|emotion-seed|archaeology|bridge)$/);
  if (match) {
    const [, projectId, chapterId, resourceName] = match;
    if (resourceName === "quality-scores") return clone(db.quality[chapterId] || []) as T;
    if (resourceName === "versions") {
      if (method === "GET") return clone(db.versions[chapterId] || []) as T;
      if (method === "POST") {
        const version = { id: id("ver"), project_id: projectId, chapter_id: chapterId, label: body?.label || "手动版本", content: body?.content || "", model: body?.model || "static-demo", context_summary: body?.context_summary || "", created_at: now() };
        db.versions[chapterId] ||= [];
        db.versions[chapterId].unshift(version);
        saveDb(db);
        return clone(version) as T;
      }
    }
    if (resourceName === "emotion-seed") return { id: id("seed"), project_id: projectId, chapter_id: chapterId, emotion_seed: "压抑的怀疑、迟来的恐惧、必须继续追查的执念。", created_at: now() } as T;
    if (resourceName === "archaeology") return [{ id: id("arch"), project_id: projectId, chapter_id: chapterId, view_mode: "demo", surface_layer: "调查推进", emotional_layer: "不安和克制", intention_layer: "主角想确认真相", subconscious_layer: "害怕真相与自己有关", resonance_layer: "读者感到旧案正在反噬现在", subconscious_leads: "录音、旧楼、门牌", motif_echoes: "雨声和电流声", reader_felt: "悬疑感和情绪余波", created_at: now() }] as T;
    if (resourceName === "bridge") return { id: id("bridge"), project_id: projectId, chapter_id: chapterId, chapter_number: 1, ending_state: "主角听到录音里的名字。", opening_hook: "下一章必须承接录音内容。", carry_over_details: "录音、周砚的反应、林晚的怀疑", emotional_residue: "震动、压抑、不敢确认", pending_threads: "录音来源是谁", created_at: now() } as T;
  }

  match = clean.match(/^\/api\/projects\/([^/]+)\/chapters\/([^/]+)\/finalize$/);
  if (match) {
    const [_, projectId, chapterId] = match;
    const ch = (db.chapters[projectId] || []).find((row) => row.id === chapterId);
    if (!ch) throw new Error("章节不存在");
    ch.status = "finalized";
    ch.updated_at = now();
    saveDb(db);
    return clone(ch) as T;
  }

  match = clean.match(/^\/api\/projects\/([^/]+)\/chapters\/([^/]+)$/);
  if (match) {
    const [_, projectId, chapterId] = match;
    const list = db.chapters[projectId] || [];
    const ch = list.find((row) => row.id === chapterId);
    if (!ch) throw new Error("章节不存在");
    if (method === "GET") return clone(ch) as T;
    if (method === "PATCH") {
      Object.assign(ch, body || {}, { word_count: wordCount(body?.draft ?? ch.draft), updated_at: now() });
      saveDb(db);
      return clone(ch) as T;
    }
    if (method === "DELETE") {
      db.chapters[projectId] = list.filter((row) => row.id !== chapterId);
      saveDb(db);
      return { ok: true } as T;
    }
  }

  match = clean.match(/^\/api\/projects\/([^/]+)\/blueprints$/);
  if (match) {
    const projectId = match[1];
    ensureProjectBuckets(db, projectId);
    if (method === "GET") return clone(db.blueprints[projectId]) as T;
    if (method === "POST") {
      const bp = createBlueprint(db, projectId, body || {});
      saveDb(db);
      return clone(bp) as T;
    }
  }

  match = clean.match(/^\/api\/projects\/([^/]+)\/blueprints\/auto-generate$/);
  if (match) {
    const projectId = match[1];
    ensureProjectBuckets(db, projectId);
    const bp = createBlueprint(db, projectId, { volume_number: body?.volume_number || 1, volume_title: "AI 自动卷蓝图" });
    saveDb(db);
    return clone(bp) as T;
  }

  match = clean.match(/^\/api\/projects\/([^/]+)\/blueprints\/([^/]+)(?:\/(approve))?$/);
  if (match) {
    const [_, projectId, blueprintId, action] = match;
    const list = db.blueprints[projectId] || [];
    const bp = list.find((row) => row.id === blueprintId);
    if (!bp) throw new Error("蓝图不存在");
    if (action === "approve") {
      bp.status = "approved";
      bp.updated_at = now();
      saveDb(db);
      return clone(bp) as T;
    }
    if (method === "GET") return clone(bp) as T;
    if (method === "PATCH") {
      Object.assign(bp, body || {}, { updated_at: now() });
      saveDb(db);
      return clone(bp) as T;
    }
    if (method === "DELETE") {
      db.blueprints[projectId] = list.filter((row) => row.id !== blueprintId);
      saveDb(db);
      return { ok: true } as T;
    }
  }

  match = clean.match(/^\/api\/projects\/([^/]+)\/jobs\/autopilot$/);
  if (match) {
    const projectId = match[1];
    ensureDemoAssets(db, projectId);
    const blueprint = db.blueprints[projectId][0] || createBlueprint(db, projectId, { volume_title: "自动托管蓝图" });
    const job = startJob(db, projectId, { ...body, blueprint_id: blueprint.id, count: body?.count || 3 });
    saveDb(db);
    return { job: clone(job), blueprint: clone(blueprint), prepared: { outlines: 1, characters: 2, relationships: 1, wiki: 4 } } as T;
  }

  match = clean.match(/^\/api\/projects\/([^/]+)\/jobs$/);
  if (match) {
    const projectId = match[1];
    ensureProjectBuckets(db, projectId);
    if (method === "GET") return clone(db.jobs[projectId]) as T;
    if (method === "POST") {
      const job = startJob(db, projectId, body || {});
      saveDb(db);
      return clone(job) as T;
    }
  }

  match = clean.match(/^\/api\/projects\/([^/]+)\/jobs\/([^/]+)\/steps$/);
  if (match) return clone(db.steps[match[2]] || []) as T;

  match = clean.match(/^\/api\/projects\/([^/]+)\/jobs\/([^/]+)(?:\/(pause|resume|abort|checkpoint\/continue))?$/);
  if (match) {
    const [_, projectId, jobId, action] = match;
    const job = (db.jobs[projectId] || []).find((row) => row.id === jobId);
    if (!job) throw new Error("任务不存在");
    if (action === "pause") job.status = "paused";
    if (action === "resume" || action === "checkpoint/continue") job.status = "running";
    if (action === "abort") job.status = "aborted";
    job.updated_at = now();
    saveDb(db);
    return clone(job) as T;
  }

  match = clean.match(/^\/api\/projects\/([^/]+)\/(emotional-leads|image-growth|bridges)$/);
  if (match) {
    const projectId = match[1];
    const name = match[2];
    if (name === "emotional-leads") return [{ id: id("lead"), project_id: projectId, chapter_id: "ch-1", lead_text: "录音里的名字让主角怀疑自己的记忆。", status: query.get("status") || "open", deepened_chapters: "2,3", created_at: now() }] as T;
    if (name === "image-growth") return [{ id: id("img"), project_id: projectId, image: query.get("image_name") || "雨声", chapter_id: "ch-1", chapter_number: 1, context: "雨声贯穿旧案线索。", felt_meaning_hint: "压抑、遮蔽、旧事重来", is_new: false, created_at: now() }] as T;
    if (name === "bridges") return (db.chapters[projectId] || []).map((ch) => ({ id: id("bridge"), project_id: projectId, chapter_id: ch.id, chapter_number: ch.chapter_number, ending_state: `${ch.title} 结束后留下新的线索。`, opening_hook: "下一章承接上一章末尾状态。", carry_over_details: "线索、情绪、未决问题", emotional_residue: "不安与追问", pending_threads: "旧案真相", created_at: now() })) as T;
  }

  match = clean.match(/^\/api\/projects\/([^/]+)\/ai\/(.+)$/);
  if (match) {
    const workflow = match[2];
    if (workflow === "test-connection") return { ok: true, status: "ok", message: "静态演示模式：不连接真实模型" } as T;
    return {
      text: `【静态演示 AI 结果】${workflow} 已生成示例内容。真实部署后这里会调用模型 API。`,
      model: "static-demo",
      status: "ok",
      error: "",
      structured: {
        title: "AI 示例记录",
        name: "AI 示例角色",
        content: "这是静态演示模式自动填充的内容。",
        analysis: "节奏克制，适合悬疑长篇。",
        chapter_goal: "推动主线并留下下一章钩子。",
      },
      context: { mode: "static-demo" },
      score: 88,
    } as T;
  }

  match = clean.match(/^\/api\/projects\/([^/]+)\/wiki\/(search|count|lint)$/);
  if (match) {
    const projectId = match[1];
    const action = match[2];
    const pages = [
      { path: "chapters/index.md", title: "章节索引", content: buildNovelMarkdown(db, projectId).slice(0, 500) },
      { path: "relationships/canvas.md", title: "关系画布", content: "林晚 -> 周砚：隐秘同盟 / 信任裂痕" },
      { path: "bridges/chapter-001-bridge.md", title: "第1章衔接包", content: "下一章必须承接录音内容。" },
    ];
    if (action === "search") return pages.filter((p) => !query.get("q") || JSON.stringify(p).includes(query.get("q") || "")) as T;
    if (action === "count") return { count: pages.length } as T;
    return { ok: true, warnings: [], missing: [], mode: "static-demo" } as T;
  }

  match = clean.match(/^\/api\/projects\/([^/]+)\/export\/manifest$/);
  if (match) {
    const projectId = match[1];
    const project = findProject(db, projectId);
    const chapters = db.chapters[projectId] || [];
    return {
      project_id: projectId,
      title: project.title,
      target_chapter_count: project.target_chapter_count,
      chapter_count: chapters.length,
      final_chapter_count: chapters.filter((ch) => ch.status === "finalized").length,
      total_words: chapters.reduce((sum, ch) => sum + (ch.word_count || 0), 0),
      average_quality_score: Math.round(chapters.reduce((sum, ch) => sum + (ch.quality_score || 0), 0) / Math.max(1, chapters.length)),
      deliverable: chapters.length > 0,
      missing_chapter_numbers: [],
      unfinished_chapters: chapters.filter((ch) => ch.status !== "finalized").map((ch) => ({ chapter_number: ch.chapter_number, title: ch.title })),
      low_quality_chapters: [],
      exports: { markdown: "static-demo", txt: "static-demo", docx: "static-demo", pdf: "static-demo", epub: "static-demo" },
    } as T;
  }

  match = clean.match(/^\/api\/projects\/([^/]+)\/([^/]+)$/);
  if (match) {
    const [_, projectId, resourceName] = match;
    ensureProjectBuckets(db, projectId);
    db.resources[projectId][resourceName] ||= [];
    if (method === "GET") return clone(db.resources[projectId][resourceName]) as T;
    if (method === "POST") {
      const row = resource(projectId, body?.title || "未命名", body?.category || "", body?.content || "", body?.payload || {});
      row.status = body?.status || "active";
      db.resources[projectId][resourceName].unshift(row);
      saveDb(db);
      return clone(row) as T;
    }
  }

  match = clean.match(/^\/api\/projects\/([^/]+)\/([^/]+)\/([^/]+)$/);
  if (match) {
    const [_, projectId, resourceName, recordId] = match;
    const rows = db.resources[projectId]?.[resourceName] || [];
    const row = rows.find((r) => r.id === recordId);
    if (!row) throw new Error("记录不存在");
    if (method === "PATCH") {
      Object.assign(row, body || {}, { updated_at: now() });
      saveDb(db);
      return clone(row) as T;
    }
    if (method === "DELETE") {
      db.resources[projectId][resourceName] = rows.filter((r) => r.id !== recordId);
      saveDb(db);
      return { ok: true } as T;
    }
  }

  throw new Error(`静态演示暂未支持接口：${method} ${path}`);
}

export function staticSubscribeSSE(path: string, onEvent: (data: any) => void): () => void {
  const match = path.match(/\/jobs\/([^/]+)\/stream/);
  const jobId = match?.[1] || "job-demo";
  const events: any[] = [{ type: "job_started" }];
  const db = loadDb();
  const job = Object.values(db.jobs).flat().find((row) => row.id === jobId);
  const start = Number(job?.start_chapter || job?.start_chapter_number || 1);
  const count = Number(job?.target_chapter_count || 3);
  for (let n = start; n < start + Math.min(count, 3); n += 1) {
    events.push({ type: "chapter_started", chapter_number: n });
    for (const step of STEPS) {
      events.push({ type: "step", chapter_number: n, step_name: step, status: "running" });
      events.push({ type: "step", chapter_number: n, step_name: step, status: "completed" });
    }
    events.push({ type: "chapter_completed", chapter_number: n });
  }
  events.push({ type: "done", status: "completed" });

  const timers = events.map((event, index) =>
    window.setTimeout(() => {
      onEvent(event);
      if (event.type === "done") completeJob(jobId);
    }, 120 + index * 180),
  );
  return () => timers.forEach((timer) => window.clearTimeout(timer));
}

export async function staticDownloadFile(path: string, filename: string): Promise<void> {
  const db = loadDb();
  const match = path.match(/\/api\/projects\/([^/]+)\/export\//);
  const projectId = match?.[1] || db.projects[0]?.id || "demo-project";
  const content = buildNovelMarkdown(db, projectId);
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}
