/**
 * EVAS Agent Control Center — Realtime Listener v2
 *
 * Supabase Realtime으로 agent_messages 감지 → OpenClaw 에이전트에 주입 → 응답을 DB에 기록
 *
 * 사용법:
 *   AGENT_ID=obsi node agent-listener.js
 *   npm start
 */

require('dotenv').config();
const { createClient } = require('@supabase/supabase-js');
const { execSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

// ── Config ──────────────────────────────────────────────────
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_KEY;
const MY_AGENT     = process.env.AGENT_ID || 'obsi';
const OPENCLAW_BIN = process.env.OPENCLAW_BIN || 'openclaw';
const BOT_TOKEN    = process.env.BOT_TOKEN;
const CHAT_ID      = process.env.CHAT_ID;
const ALL_AGENTS   = ['obsi', 'rise', 'lab', 'art'];
const DEBATE_GROUP = process.env.DEBATE_GROUP || '-1003834471717';

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

// ── Agent Injection ──────────────────────────────────────────
async function injectToAgent(msg) {
  const prompt = [
    `[Agent Control Center — ${TYPE_LABEL[msg.type] || msg.type}]`,
    `From: ${msg.from_agent}`,
    msg.subject ? `Subject: ${msg.subject}` : '',
    `Message: ${msg.message}`,
    '',
    `이 메시지에 대해 응답해주세요. 응답은 간결하게 (3줄 이내).`,
    `응답 형식: 핵심 내용만. 인사말 불필요.`
  ].filter(Boolean).join('\n');

  try {
    // 줄바꿈을 공백으로 치환해서 한 줄로
    const oneline = prompt.replace(/\n/g, ' ').replace(/'/g, '');
    const result = execSync(
      `${OPENCLAW_BIN} agent --agent main --timeout 60000 --message '${oneline}'`,
      { timeout: 120000, encoding: 'utf-8', maxBuffer: 10 * 1024 * 1024, env: { ...process.env, PATH: `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:${process.env.PATH || ""}` } }
    ).trim();

    console.log(`[${MY_AGENT} 응답] ${result.slice(0, 200)}`);
    return result;
  } catch (err) {
    console.error(`Agent injection 실패: ${err.message}`);
    return null;
  }
}

async function writeResponse(messageId, response) {
  if (!response) return;
  try {
    // 기존 responses 가져오기
    const { data } = await supabase
      .from('agent_messages')
      .select('responses, to_agents')
      .eq('id', messageId)
      .single();
    
    const responses = data?.responses || {};
    responses[MY_AGENT] = response.slice(0, 1000);

    const targets = (data?.to_agents || []).includes('all') ? ALL_AGENTS : (data?.to_agents || []);
    const allResponded = targets.every(a => responses[a]);

    await supabase
      .from('agent_messages')
      .update({ 
        responses, 
        status: allResponded ? 'completed' : 'partial' 
      })
      .eq('id', messageId);
    
    console.log(`[${MY_AGENT}] 응답 기록 완료 → ${messageId.slice(0, 8)}`);
  } catch (err) {
    console.error('writeResponse 실패:', err.message);
  }
}

// ── Handlers ────────────────────────────────────────────────
async function handleInsert(payload) {
  const msg = payload.new;
  if (!msg.to_agents.includes(MY_AGENT) && !msg.to_agents.includes('all')) return;
  if (msg.from_agent === MY_AGENT) return; // 자기 메시지 무시

  console.log(`[${msg.type}] from ${msg.from_agent}: ${msg.subject || ''}`);
  
  // 1. 알림 (debate는 그룹으로, 그 외는 개인챗)
  if (msg.type === 'debate_turn' || msg.type === 'debate') {
    // debate는 그룹에서만
  } else {
    await sendTelegram(formatMessage(msg));
  }
  await markAsRead(msg.id);
  
  // 2. 에이전트에 주입 → 응답 받기 → DB 기록
  if (msg.type === 'debate_turn') {
    await handleDebateTurn(msg);
  } else if (msg.type !== 'debate') {
    const response = await injectToAgent(msg);
    if (response) {
      await writeResponse(msg.id, response);
      await sendTelegram(`💬 <b>[${MY_AGENT} 응답]</b>\n${response.slice(0, 2000)}`);
    }
  }
}

// ── Debate Turn Handler ──────────────────────────────────────
async function handleDebateTurn(msg) {
  const meta = msg.context || {};
  const debateId = meta.debate_id;
  const round = meta.round || 1;
  const maxRounds = meta.max_rounds || 3;

  // 중복 방지: 자기 응답이 이미 있으면 skip
  if (msg.responses && msg.responses[MY_AGENT]) return;
  const { data: freshMsg } = await supabase.from('agent_messages').select('status,responses').eq('id', msg.id).single();
  if (freshMsg?.responses && freshMsg.responses[MY_AGENT]) return;

  console.log(`[DEBATE_TURN R${round}] ${msg.subject} — ${MY_AGENT} 응답 중...`);

  // 메인 debate 메시지에서 이전 라운드 가져오기
  let prevContext = '';
  if (debateId) {
    try {
      const { data } = await supabase.from('agent_messages').select('debate_rounds, subject').eq('id', debateId).single();
      const rounds = data?.debate_rounds || {};
      for (let r = 1; r < round; r++) {
        const rd = rounds[String(r)] || {};
        for (const [agent, opinion] of Object.entries(rd)) {
          prevContext += `Round ${r} — ${agent}: ${opinion}\n`;
        }
      }
    } catch (e) {}
  }

  const prompt = [
    `[DEBATE Round ${round}/${maxRounds}]`,
    msg.body || msg.message,
    prevContext ? `\n이전 의견:\n${prevContext}` : '',
    '\n응답은 3-5문장으로 간결하게. 핵심만.'
  ].filter(Boolean).join('\n');

  const oneline = prompt.replace(/\n/g, ' ').replace(/'/g, '');
  try {
    const result = execSync(
      `${OPENCLAW_BIN} agent --agent main --timeout 60000 --message '${oneline}'`,
      { timeout: 120000, encoding: 'utf-8', maxBuffer: 10 * 1024 * 1024,
        env: { ...process.env, PATH: `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:${process.env.PATH || ''}` }
      }
    ).trim();

    console.log(`[DEBATE_TURN R${round}] ${MY_AGENT}: ${result.slice(0, 150)}`);

    // debate_turn 메시지를 completed로
    await supabase.from('agent_messages').update({ status: 'completed', responses: { [MY_AGENT]: result.slice(0, 500) } }).eq('id', msg.id);

    // 메인 debate 메시지의 debate_rounds 업데이트 (retry로 race condition 방지)
    if (debateId) {
      // 500ms 딜레이 (봇마다 약간 다른 타이밍)
      await new Promise(r => setTimeout(r, Math.random() * 2000 + 500));
      
      const { data } = await supabase.from('agent_messages').select('debate_rounds, debate_config, to_agents').eq('id', debateId).single();
      const rounds = data?.debate_rounds || {};
      const cfg = data?.debate_config || {};
      const roundData = rounds[String(round)] || {};
      roundData[MY_AGENT] = result.slice(0, 500);
      rounds[String(round)] = roundData;

      const participants = cfg.participants || data.to_agents.filter(a => a !== 'all');
      const allAnswered = participants.every(a => roundData[a]);

      const update = { debate_rounds: rounds };
      if (allAnswered && round < maxRounds) {
        // 다음 라운드 시작
        cfg.current_round = round + 1;
        update.debate_config = cfg;
        update.status = 'active';
        
        // 다음 라운드 메시지 전송
        for (const agent of participants) {
          await supabase.from('agent_messages').insert({
            from_agent: 'system',
            to_agents: [agent],
            type: 'debate_turn',
            subject: `[토론 Round ${round + 1}] ${data?.subject || ''}`,
            body: `토론을 계속합니다. 이전 의견을 참고하여 ${round + 1 === maxRounds ? '최종 합의안' : '반론 또는 보충'}을 제시해주세요.`,
            status: 'pending',
            context: { debate_id: debateId, round: round + 1, max_rounds: maxRounds }
          });
        }
      } else if (allAnswered && round >= maxRounds) {
        update.status = 'completed';
      }

      await supabase.from('agent_messages').update(update).eq('id', debateId);
    }

    await sendToGroup(`🗣️ <b>[Round ${round}] ${MY_AGENT}</b>\n${result.slice(0, 2000)}`);
  } catch (err) {
    console.error(`DEBATE_TURN 응답 실패: ${err.message}`);
    // 실패해도 에러 기록
    await supabase.from('agent_messages').update({ 
      status: 'completed', 
      responses: { [MY_AGENT]: `⚠️ 응답 실패: ${err.message.slice(0, 100)}` } 
    }).eq('id', msg.id);
  }
}

// ── 그룹챗으로 토론 응답 ──────────────────────────────────
async function sendToGroup(text) {
  if (!BOT_TOKEN) return;
  try {
    const res = await fetch(
      `https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: DEBATE_GROUP,
          text: text.slice(0, 4000),
          parse_mode: 'HTML',
          disable_web_page_preview: true,
        }),
      }
    );
    if (!res.ok) console.error(`Group send HTTP ${res.status}`);
  } catch (err) {
    console.error('Group 전송 실패:', err.message);
  }
}

async function handleDebateUpdate(payload) {
  // debate_turn 방식으로 전환 — UPDATE 핸들러는 비활성화
  // (debate_turn INSERT가 각 에이전트에게 개별 전달)
  return;

  const cfg   = msg.debate_config || {};
  const round = cfg.current_round || 1;
  const rounds = msg.debate_rounds || {};
  const mine  = rounds[String(round)] || {};
  if (mine[MY_AGENT]) return; // already answered

  // 이전 라운드 컨텍스트 수집
  const prevRounds = [];
  for (let r = 1; r < round; r++) {
    const rd = rounds[String(r)] || {};
    for (const [agent, opinion] of Object.entries(rd)) {
      prevRounds.push(`Round ${r} - ${agent}: ${opinion}`);
    }
  }

  const prompt = [
    `[DEBATE Round ${round}/${cfg.max_rounds || 3}]`,
    `주제: ${msg.subject}`,
    `원문: ${msg.message}`,
    prevRounds.length ? `\n이전 의견:\n${prevRounds.join('\n')}` : '',
    '',
    round === 1 ? '당신의 의견을 제시해주세요.' :
    round === (cfg.max_rounds || 3) ? '최종 합의안을 제시해주세요.' :
    '이전 의견에 대한 반론 또는 보충 의견을 제시해주세요.',
    '응답은 3줄 이내로 간결하게.'
  ].filter(Boolean).join('\n');

  console.log(`[DEBATE R${round}] ${msg.subject} — ${MY_AGENT} 응답 중...`);
  
  const oneline = prompt.replace(/\n/g, ' ').replace(/'/g, '');
  try {
    const result = execSync(
      `${OPENCLAW_BIN} agent --agent main --timeout 60000 --message '${oneline}'`,
      { timeout: 120000, encoding: 'utf-8', maxBuffer: 10 * 1024 * 1024, env: { ...process.env, PATH: `/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:${process.env.PATH || ""}` } }
    ).trim();

    // debate_rounds 업데이트
    const roundData = rounds[String(round)] || {};
    roundData[MY_AGENT] = result.slice(0, 500);
    rounds[String(round)] = roundData;

    const participants = cfg.participants || msg.to_agents.filter(a => a !== 'all');
    const allAnswered = participants.every(a => roundData[a]);

    const update = { debate_rounds: rounds };
    if (allAnswered && round < (cfg.max_rounds || 3)) {
      cfg.current_round = round + 1;
      update.debate_config = cfg;
    } else if (allAnswered && round >= (cfg.max_rounds || 3)) {
      update.status = 'completed';
    }

    await supabase.from('agent_messages').update(update).eq('id', msg.id);
    console.log(`[DEBATE R${round}] ${MY_AGENT} 응답 완료: ${result.slice(0, 100)}`);
    await sendToGroup(`🗣️ <b>[DEBATE R${round}] ${MY_AGENT}</b>\n${result.slice(0, 2000)}`);
  } catch (err) {
    console.error(`DEBATE 응답 실패: ${err.message}`);
  }
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
