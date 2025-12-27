import OpenAI from "openai";
import Anthropic from "@anthropic-ai/sdk";
import {
  applyRuleBasedFix,
  cleanupTemp,
  encodeFileBase64,
  deriveOutputPath,
  parseEpubPayload,
  validateEpubStructure,
  writeTempEpub,
} from "../lib/epubTools.js";

const MAX_RETURN_BYTES = Number(process.env.MAX_RETURN_BYTES || 5 * 1024 * 1024);
const OPENAI_SYSTEM_PROMPT =
  "You are an EPUB repair tool. Call the provided tools to validate, fix, and re-validate. " +
  "Keep replies brief and mention if validation is structural-only.";
const CLAUDE_SYSTEM_PROMPT =
  "You are an EPUB repair tool. Use the provided tools to validate, fix, and re-validate. " +
  "Keep replies concise and mention structural-only validation.";

function allowCors(res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
  res.setHeader("Access-Control-Allow-Methods", "OPTIONS, POST");
}

async function prepareEpub(payload) {
  const cleanup = [];
  const buffer = await parseEpubPayload(payload);
  const path = await writeTempEpub(buffer);
  cleanup.push(path);
  return { epubPath: path, cleanup };
}

function buildUserPrompt(epubPath, outputPath, goal) {
  const parts = [];
  if (goal) parts.push(`Goal: ${goal}`);
  parts.push(`EPUB: ${epubPath}`);
  if (outputPath) parts.push(`Output: ${outputPath}`);
  parts.push("Use validate_epub and apply_rule_based_fix as needed.");
  return parts.join("\n");
}

async function runTool(name, args) {
  if (name === "validate_epub") {
    return validateEpubStructure(args.epub_path);
  }
  if (name === "apply_rule_based_fix") {
    return applyRuleBasedFix(args.epub_path, args.output_path);
  }
  return { success: false, errors: [`Unknown tool: ${name}`] };
}

async function runOpenAIAgent(payload, epubPath, outputPath) {
  const client = new OpenAI({
    apiKey: payload.api_key || process.env.OPENAI_API_KEY,
    baseURL: payload.base_url || process.env.OPENAI_BASE_URL || undefined,
  });
  const model = payload.model || process.env.OPENAI_MODEL || "gpt-4.1-mini";
  const temperature =
    typeof payload.temperature === "number"
      ? payload.temperature
      : Number(process.env.OPENAI_TEMPERATURE || 0.2);
  const maxTurns = payload.max_turns || 4;

  const tools = [
    {
      type: "function",
      function: {
        name: "validate_epub",
        description: "Validate EPUB structure.",
        parameters: {
          type: "object",
          properties: { epub_path: { type: "string" } },
          required: ["epub_path"],
        },
      },
    },
    {
      type: "function",
      function: {
        name: "apply_rule_based_fix",
        description: "Run deterministic EPUB fixer (pass-through in Node).",
        parameters: {
          type: "object",
          properties: {
            epub_path: { type: "string" },
            output_path: { type: "string" },
          },
          required: ["epub_path"],
        },
      },
    },
  ];

  const messages = [
    { role: "system", content: OPENAI_SYSTEM_PROMPT },
    { role: "user", content: buildUserPrompt(epubPath, outputPath, payload.goal) },
  ];

  const transcript = [];
  let reply = "";

  for (let turn = 0; turn < maxTurns; turn += 1) {
    const response = await client.chat.completions.create({
      model,
      temperature,
      messages,
      tools,
      tool_choice: "auto",
    });
    const message = response.choices[0].message;
    if (message.tool_calls?.length) {
      messages.push(message);
      for (const toolCall of message.tool_calls) {
        let args = {};
        try {
          args = JSON.parse(toolCall.function.arguments || "{}");
        } catch {
          transcript.push({ type: "error", message: "Failed to parse tool arguments" });
          continue;
        }
        const result = await runTool(toolCall.function.name, args);
        transcript.push({
          type: "tool_call",
          name: toolCall.function.name,
          result,
        });
        messages.push({
          role: "tool",
          tool_call_id: toolCall.id,
          content: JSON.stringify(result),
        });
      }
      continue;
    }
    reply = message.content || "";
    return { success: true, reply, transcript, model };
  }

  return { success: false, reply, transcript, model, errors: ["Max turns reached."] };
}

async function runClaudeAgent(payload, epubPath, outputPath) {
  const client = new Anthropic({
    apiKey: payload.api_key || process.env.ANTHROPIC_API_KEY,
  });
  const model =
    payload.model || process.env.CLAUDE_MODEL || "claude-3-5-sonnet-20241022";
  const temperature =
    typeof payload.temperature === "number"
      ? payload.temperature
      : Number(process.env.CLAUDE_TEMPERATURE || 0);
  const maxTurns = payload.max_turns || 4;

  const tools = [
    {
      name: "validate_epub",
      description: "Validate EPUB structure.",
      input_schema: {
        type: "object",
        properties: { epub_path: { type: "string" } },
        required: ["epub_path"],
      },
    },
    {
      name: "apply_rule_based_fix",
      description: "Run deterministic EPUB fixer (pass-through in Node).",
      input_schema: {
        type: "object",
        properties: {
          epub_path: { type: "string" },
          output_path: { type: "string" },
        },
        required: ["epub_path"],
      },
    },
  ];

  const messages = [
    {
      role: "user",
      content: buildUserPrompt(epubPath, outputPath, payload.goal),
    },
  ];
  const transcript = [];
  let reply = "";

  for (let turn = 0; turn < maxTurns; turn += 1) {
    const response = await client.messages.create({
      model,
      temperature,
      max_tokens: 800,
      system: CLAUDE_SYSTEM_PROMPT,
      tools,
      messages,
    });

    const toolUses = response.content.filter((item) => item.type === "tool_use");
    const textChunks = response.content
      .filter((item) => item.type === "text")
      .map((item) => item.text)
      .join(" ");

    if (toolUses.length) {
      // Add the assistant's response (with tool_use) to messages first
      messages.push({ role: "assistant", content: response.content });

      const toolResults = [];
      for (const toolUse of toolUses) {
        const result = await runTool(toolUse.name, toolUse.input || {});
        transcript.push({
          type: "tool_call",
          name: toolUse.name,
          result,
        });
        toolResults.push({
          type: "tool_result",
          tool_use_id: toolUse.id,
          content: JSON.stringify(result),
        });
      }
      messages.push({ role: "user", content: toolResults });
      continue;
    }

    reply = textChunks.trim();
    return { success: true, reply, transcript, model };
  }

  return { success: false, reply, transcript, model, errors: ["Max turns reached."] };
}

async function handler(req, res) {
  allowCors(res);
  if (req.method === "OPTIONS") {
    res.status(204).end();
    return;
  }
  if (req.method !== "POST") {
    res.status(405).json({ success: false, errors: ["POST only."] });
    return;
  }

  let payload = {};
  try {
    payload = typeof req.body === "string" ? JSON.parse(req.body || "{}") : req.body || {};
  } catch {
    res.status(400).json({ success: false, errors: ["Invalid JSON body."] });
    return;
  }

  let epubPath;
  const cleanup = [];
  try {
    const prep = await prepareEpub(payload);
    epubPath = prep.epubPath;
    cleanup.push(...prep.cleanup);
  } catch (err) {
    res.status(400).json({ success: false, errors: [err.message] });
    return;
  }

  const outputPath = deriveOutputPath(epubPath, payload.output_name);
  const warnings = [];

  let agentResult;
  try {
    if ((payload.provider || "openai").toLowerCase() === "claude") {
      agentResult = await runClaudeAgent(payload, epubPath, outputPath);
    } else {
      agentResult = await runOpenAIAgent(payload, epubPath, outputPath);
    }
  } catch (err) {
    agentResult = { success: false, errors: [err.message] };
  }

  // Always run the fixer to ensure output exists even if agent skipped tool calls
  const fixResult = await applyRuleBasedFix(epubPath, outputPath);
  // Output files live in temp storage; clean them up after responding.
  cleanup.push(outputPath);
  const validation = payload.validate === false ? null : await validateEpubStructure(outputPath);

  const response = {
    provider: (payload.provider || "openai").toLowerCase(),
    success:
      agentResult?.success !== false &&
      fixResult?.success !== false &&
      (validation ? validation.success !== false : true),
    agent_result: agentResult,
    fix_result: fixResult,
    validation,
    output_path: outputPath,
    warnings,
  };

  if (payload.return_base64) {
    const fileBlob = await encodeFileBase64(outputPath, MAX_RETURN_BYTES);
    response.output_base64 = fileBlob.data;
    response.output_truncated = fileBlob.truncated || false;
    if (fileBlob.errors.length) {
      response.file_errors = fileBlob.errors;
      response.success = false;
    }
  }

  res.status(response.success ? 200 : 500).json(response);

  await cleanupTemp(cleanup);
}

export default handler;
