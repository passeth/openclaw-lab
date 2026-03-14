/**
 * EVAS Agent Control Center — Realtime Listener
 *
 * Supabase Realtime으로 agent_messages 감지 → 텔레그램 전송
 *
 * 사용법:
 *   AGENT_ID=obsi node agent-listener.js
 *   npm start
 */

require('dotenv').config();
const { createClient } = require('@supabase/supabase-js');

// ── Config ──────────────────────────────────────────────────
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_KEY;
const MY_AGENT     = process.env.AGENT_ID || 'obsi';
const BOT_TOKEN    = process.env.BOT_TOKEN;
const CHAT_ID      = process.env.CHAT_ID;
const ALL_AGENTS   = ['obsi', 'rise', 'lab', 'art'];

if (!SUPABASE_URL || !SUPABASE_KEY) {
  console.error('SUPABASE_URL / SUPABASE_SERVICE_KEY 환경변수 필요');
  process.exit(1);
}

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

// ── Telegram ────────────────────────────────────────────────
async function sendTelegram(text) {
  if (!BOT_TOKEN || !CHAT_ID) return;
  try {
    const res = await fetch(
      `https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: CHAT_ID,
          text: text.slice(0, 4000),
          parse_mode: 'HTML',
          disable_web_page_preview: true,
        }),
      }
    );
    if (!res.ok) console.error(`Telegram HTTP ${res.status}`);
  } catch (err) {
    console.error('Telegram 전송 실패:', err.message);
  }
}

// ── Mark as Read ────────────────────────────────────────────
async function markAsRead(messageId) {
  try {
    const { data, error } = await supabase
      .from('agent_messages')
      .select('read_by, to_agents')
      .eq('id', messageId)
      .single();
    if (error) throw error;

    const readBy = data.read_by || [];
    if (readBy.includes(MY_AGENT)) return;
    readBy.push(MY_AGENT);

    const targets = data.to_agents.includes('all') ? ALL_AGENTS : data.to_agents;
    const allRead = targets.every((a) => readBy.includes(a));

    await supabase
      .from('agent_messages')
      .update({ read_by: readBy, status: allRead ? 'completed' : 'partial' })
      .eq('id', messageId);
  } catch (err) {
    console.error('markAsRead 실패:', err.message);
  }
}

// ── Format ──────────────────────────────────────────────────
const TYPE_LABEL = {
  broadcast: '📢 BROADCAST',
  multicast: '🎯 MULTICAST',
  direct:    '💬 DIRECT',
  debate:    '🗣️ DEBATE',
};

function formatMessage(msg) {
  const label = TYPE_LABEL[msg.type] || msg.type.toUpperCase();
  let t = `<b>[${label}]</b> from <b>${msg.from_agent}</b>\n`;
  if (msg.type === 'multicast') t += `To: ${msg.to_agents.join(', ')}\n`;
  if (msg.subject) t += `<b>${msg.subject}</b>\n`;
  t += `\n${msg.message}`;
  return t;
}

// ── Handlers ────────────────────────────────────────────────
async function handleInsert(payload) {
  const msg = payload.new;
  if (!msg.to_agents.includes(MY_AGENT) && !msg.to_agents.includes('all')) return;

  console.log(`[${msg.type}] from ${msg.from_agent}: ${msg.subject || ''}`);
  await sendTelegram(formatMessage(msg));
  await markAsRead(msg.id);
}

async function handleDebateUpdate(payload) {
  const msg = payload.new;
  if (msg.type !== 'debate') return;
  if (!msg.to_agents.includes(MY_AGENT) && !msg.to_agents.includes('all')) return;

  const cfg   = msg.debate_config || {};
  const round = cfg.current_round || 1;
  const mine  = (msg.debate_rounds || {})[String(round)] || {};
  if (mine[MY_AGENT]) return; // already answered

  const prev = (msg.debate_rounds || {})[String(round - 1)] || {};
  const prevText = Object.entries(prev)
    .map(([a, o]) => `<b>${a}</b>: ${String(o).slice(0, 300)}`)
    .join('\n');

  let t = `🗣️ <b>[DEBATE Round ${round}/${cfg.max_rounds || '?'}]</b>\n<b>${msg.subject}</b>\n\n`;
  if (round > 1 && prevText) t += `이전 라운드:\n${prevText}\n\n`;
  t += '💭 의견을 제시해주세요.';

  await sendTelegram(t);
}

// ── Subscribe ───────────────────────────────────────────────
let channel;
function subscribe() {
  channel = supabase
    .channel('agent-hub')
    .on('postgres_changes',
      { event: 'INSERT', schema: 'public', table: 'agent_messages' },
      handleInsert)
    .on('postgres_changes',
      { event: 'UPDATE', schema: 'public', table: 'agent_messages' },
      handleDebateUpdate)
    .subscribe((status, err) => {
      if (status === 'SUBSCRIBED') console.log(`Realtime 연결 — "${MY_AGENT}" 리스닝`);
      else if (err) console.error('Channel error:', err.message);
      else console.log(`Realtime: ${status}`);
    });
}

// ── Main ────────────────────────────────────────────────────
subscribe();

setInterval(() => console.log(`[${MY_AGENT}] alive ${new Date().toISOString()}`), 60_000);

function shutdown(sig) {
  console.log(`${sig} — 종료`);
  if (channel) supabase.removeChannel(channel);
  process.exit(0);
}
process.on('SIGINT',  () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));

console.log(`${MY_AGENT} listener started | ${SUPABASE_URL} | telegram=${BOT_TOKEN ? 'ON' : 'OFF'}`);
