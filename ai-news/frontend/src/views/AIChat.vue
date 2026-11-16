<template>
  <div class="ai-chat-container">
    <header class="chat-page-header"><div><span class="eyebrow">AI CHAT</span><h1>AI 问答<span class="header-spark">✳</span></h1></div><button class="quiet-button" @click="newConversation"><van-icon name="plus" /> 新对话</button></header>
    <div class="chat-content">
      <div class="chat-toolbar"><span class="assistant-identity"><span class="assistant-mark">✳</span><strong>AI 助手</strong></span><button class="connection-status" @click="checkService"><span :class="['status-dot', { ready: configured }]" />{{ configured ? '随时为你解答' : '点击检查连接' }}</button></div>
      <div class="messages-container" ref="messagesContainer" role="log" aria-label="与 AI 助手的对话" aria-live="polite" :aria-busy="isLoading">
        <article v-for="(message, index) in messages" :key="message.id" :class="['message', message.role === 'user' ? 'user-message' : 'ai-message']">
          <div class="message-author"><span class="message-avatar">{{ message.role === 'user' ? '你' : '✳' }}</span><strong>{{ message.role === 'user' ? '你' : 'AI 助手' }}</strong><span v-if="message.status === 'streaming'" class="generating-label">正在组织回答…</span></div>
          <div class="message-content">
            <div v-if="message.role === 'assistant' && !message.content && message.status === 'streaming'" class="typing-indicator"><span /><span /><span /></div>
            <div v-else v-html="formatMessage(message.content)" />
            <p v-if="message.error" class="message-error" role="alert">{{ message.error }}</p>
          </div>
          <div v-if="message.role === 'assistant' && message.status !== 'streaming'" class="message-actions"><span v-if="message.status === 'stopped'">已停止生成</span><button v-if="message.content" aria-label="复制回答" @click="copyMessage(message.content)"><van-icon name="description-o" /> 复制</button><button v-if="index === messages.length - 1 && !isLoading" aria-label="重新生成" @click="regenerateResponse"><van-icon name="replay" /> 重新生成</button></div>
        </article>
      </div>
      <div class="composer-wrap"><div class="input-container"><van-field v-model="userInput" rows="1" :autosize="{ minHeight: 28, maxHeight: 140 }" type="textarea" placeholder="输入你的问题…" class="chat-input" maxlength="20000" @keydown="handleEnter" /><button v-if="isLoading" class="send-button stop-button" @click="stopGeneration" aria-label="停止生成"><span /></button><button v-else class="send-button" :disabled="!userInput.trim()" @click="sendMessage()" aria-label="发送消息"><van-icon name="arrow-up" /></button></div><div class="composer-hint"><span>Enter 发送 · Shift + Enter 换行</span><span>AI 回答仅供参考，请核实重要信息</span></div></div>
    </div>
    <tab-bar />
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch, onBeforeUnmount, onDeactivated } from 'vue';
import TabBar from '../components/TabBar.vue';
import { showToast } from 'vant';
import * as marked from 'marked';
import DOMPurify from 'dompurify';
import { aiChatConfig } from '../config/api';
import { streamChat } from '../services/ai';

// 聊天消息
const messages = ref([]);
const userInput = ref('');
const messagesContainer = ref(null);
const isLoading = ref(false);
let controller = null;
let messageSequence = 0;

// 从配置文件获取API设置
const apiEndpoint = ref(aiChatConfig.apiEndpoint);
const configured = ref(null);

// 格式化消息内容（支持Markdown）
const formatMessage = (content) => {
  if (!content) return '';
  // 使用marked解析Markdown，并用DOMPurify清理HTML
  return DOMPurify.sanitize(marked.parse(content));
};

// 发送消息
const sendMessage = async () => {
  if (!userInput.value.trim() || isLoading.value) return;
  isLoading.value = true;
  
  // 检查API设置
  if (configured.value === false) {
    await checkService();
    if (configured.value === false) {
      showToast('AI 助手暂未启用，请联系管理员');
      isLoading.value = false;
      return;
    }
  }
  
  // 添加用户消息
  const userMessage = userInput.value.trim();
  messages.value.push({ id: ++messageSequence, role: 'user', content: userMessage });
  userInput.value = '';
  
  // 添加AI消息占位
  messages.value.push({ id: ++messageSequence, role: 'assistant', content: '', status: 'streaming' });
  const reply = messages.value[messages.value.length - 1];
  
  // 滚动到底部
  await nextTick();
  scrollToBottom();
  
  // 发送请求
  isLoading.value = true;
  controller = new AbortController();
  try {
    await fetchAIResponse(userMessage, reply, controller.signal);
    reply.status = 'done';
  } catch (error) {
    if (error.name === 'AbortError') {
      reply.status = 'stopped';
    } else {
      console.error('Error fetching AI response:', error);
      // 更新最后一条消息为错误信息
      reply.error = error.message || '暂时无法连接助手，请稍后重试。';
      reply.status = 'error';
    }
  } finally {
    isLoading.value = false;
    controller = null;
    await nextTick();
    scrollToBottom();
  }
};

// 获取AI响应（使用SSE）
const fetchAIResponse = async (userMessage, reply, signal) => {
  const allMessages = messages.value
    .slice(0, -1) // 排除最后一个空的assistant消息
    .filter(msg => msg.content.trim())
    .map(msg => ({ role: msg.role, content: msg.content }));
  
  try {
    // 添加阿里云DashScope所需的SSE头
    // 适配阿里云DashScope的返回格式
    // 供应商请求头与协议适配现由后端完成。
    // 处理SSE流
    await streamChat(apiEndpoint.value, allMessages, { signal, onDelta: async (content) => {
      // 更新最后一条消息
      reply.content += content;
      await nextTick();
      scrollToBottom();
    } });
    // 如果没有收到任何内容
    if (!reply.content) throw new Error('助手暂时没有返回内容，请重试。');
  } catch (error) {
    console.error('Fetch error:', error);
    throw error;
  }
};

// 滚动到底部
const scrollToBottom = () => {
  if (messagesContainer.value && messages.value.length) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

const checkService = async () => {
  try {
    const response = await fetch(aiChatConfig.configEndpoint);
    if (!response.ok) throw new Error('服务暂不可用');
    const payload = await response.json();
    configured.value = Boolean(payload.data?.configured);
  } catch {
    configured.value = null;
  }
};
const handleEnter = (event) => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    sendMessage();
  }
};
const stopGeneration = () => controller?.abort();
const newConversation = () => {
  stopGeneration();
  messages.value = [];
  userInput.value = '';
};
const regenerateResponse = () => {
  if (isLoading.value) return;
  if (messages.value.at(-1)?.role === 'assistant') messages.value.pop();
  const question = messages.value.pop();
  if (question?.role === 'user') {
    userInput.value = question.content;
    sendMessage();
  }
};
const copyMessage = async (content) => {
  try {
    await navigator.clipboard.writeText(content);
    showToast('回答已复制');
  } catch {
    showToast('复制失败，请长按选择文字复制');
  }
};

// 监听消息变化，自动滚动
watch(messages, () => {
  nextTick(scrollToBottom);
}, { deep: true });

// 组件挂载时滚动到底部
onMounted(() => {
  scrollToBottom();
  checkService();
});
onBeforeUnmount(stopGeneration);
onDeactivated(stopGeneration);
</script>

<style scoped>
.ai-chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding-top: 46px;
  padding-bottom: 50px;
  box-sizing: border-box;
}

.chat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.message {
  margin-bottom: 10px;
  max-width: 80%;
}

.user-message {
  margin-left: auto;
}

.ai-message {
  margin-right: auto;
}

.message-content {
  padding: 10px;
  border-radius: 10px;
  word-break: break-word;
}

.user-message .message-content {
  background-color: #007aff;
  color: white;
}

.ai-message .message-content {
  background-color: #f2f2f2;
  color: #333;
}

.input-container {
  display: flex;
  padding: 10px;
  border-top: 1px solid #eee;
  background-color: #fff;
}

.chat-input {
  flex: 1;
  margin-right: 10px;
}

.send-button {
  align-self: flex-end;
}

/* Markdown 样式 */
.message-content pre {
  background-color: #f8f8f8;
  padding: 10px;
  border-radius: 5px;
  overflow-x: auto;
}

.message-content code {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 2px 4px;
  border-radius: 3px;
}

.message-content img {
  max-width: 100%;
}

/* 打字指示器 */
.typing-indicator {
  display: flex;
  padding: 5px;
}

.typing-indicator span {
  height: 8px;
  width: 8px;
  background-color: #999;
  border-radius: 50%;
  margin: 0 2px;
  display: inline-block;
  animation: bounce 1.5s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes bounce {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-5px);
  }
}

/* Markdown样式 */
:deep(pre) {
  background-color: #f0f0f0;
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
}

:deep(code) {
  font-family: monospace;
  background-color: #f0f0f0;
  padding: 2px 4px;
  border-radius: 4px;
}

:deep(p) {
  margin: 8px 0;
}

:deep(ul), :deep(ol) {
  padding-left: 20px;
}

:deep(a) {
  color: #1989fa;
  text-decoration: none;
}

.ai-chat-container { height: 100dvh; padding: 28px 40px 26px; max-width: 1180px; margin: auto; background: var(--background-color); }
.chat-page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 22px; flex-shrink: 0; }.chat-page-header h1 { font-size: 23px; font-weight: 650; letter-spacing: 1px; margin-top: 7px; }.header-spark { color: var(--primary-color); margin-left: 10px; font-size: 25px; }
.quiet-button { display: flex; align-items: center; gap: 7px; background: var(--surface-color); border: 1px solid var(--border-color); color: var(--text-color); padding: 10px 16px; font-size: 12px; border-radius: 7px; cursor: pointer; }
.chat-content { border: 1px solid var(--border-color); border-radius: 14px; background: var(--surface-color); box-shadow: 0 8px 45px #29271e04; min-height: 0; }.chat-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid var(--border-color); flex-shrink: 0; }.assistant-identity { display: flex; align-items: center; gap: 9px; font-size: 12px; }.assistant-identity strong { font-weight: 550; }.assistant-mark { color: var(--primary-color); font-size: 26px; }.connection-status { display: flex; align-items: center; gap: 6px; border: none; background: none; font-size: 10px; color: var(--text-color-light); cursor: pointer; }.status-dot { width: 5px; height: 5px; border-radius: 50%; background: #b3b6ae; }.status-dot.ready { background: #6e8967; }
.messages-container { padding: 28px 38px; overscroll-behavior: contain; min-height: 0; }
.message { max-width: 100%; margin-bottom: 32px; }.message-author { display: flex; gap: 9px; align-items: center; font-size: 11px; margin-bottom: 10px; }.message-author strong { font-weight: 600; }.message-avatar { width: 26px; height: 26px; border-radius: 7px; background: var(--accent-soft); color: var(--primary-color); display: grid; place-items: center; font-size: 18px; }.generating-label { color: var(--text-color-lighter); font-size: 10px; font-weight: 400; }.message-content { padding: 0 0 0 35px; font-size: 14px; line-height: 1.9; }.ai-message .message-content { background: none; color: var(--text-color); }.user-message { max-width: 85%; margin-left: auto; }.user-message .message-author { justify-content: flex-end; }.user-message .message-avatar { background: #e4e7df; color: #596351; font-size: 11px; }.user-message .message-content { padding: 13px 18px; background: var(--accent-soft); color: var(--text-color); border-radius: 10px 0 10px 10px; }.message-actions { display: flex; gap: 15px; align-items: center; padding-left: 35px; margin-top: 12px; color: var(--text-color-lighter); font-size: 10px; }.message-actions button { border: none; padding: 0; background: none; color: var(--text-color-lighter); cursor: pointer; font-size: 10px; display: flex; gap: 4px; align-items: center; }.message-actions button:hover { color: var(--primary-color); }.message-error { font-size: 12px; color: #b65a3f; padding: 10px 0; }
.composer-wrap { padding: 15px 26px 16px; flex-shrink: 0; }.input-container { padding: 12px 13px 12px 17px; align-items: flex-end; background: var(--background-color); border: 1px solid var(--border-color); border-radius: 10px; gap: 8px; transition: border-color .2s; }.input-container:focus-within { border-color: var(--primary-color); }.ai-chat-container .input-container .chat-input { background: transparent; padding: 2px 0; margin: 0; }.chat-input :deep(.van-field__control) { font-size: 13px; color: var(--text-color); line-height: 26px; }.send-button { height: 34px; width: 34px; border: 0; border-radius: 8px; background: var(--primary-color); color: white; font-size: 21px; display: grid; place-items: center; cursor: pointer; flex-shrink: 0; }.send-button:disabled { opacity: .4; cursor: default; }.stop-button > span { width: 11px; height: 11px; border-radius: 2px; background: white; }.composer-hint { display: flex; justify-content: space-between; font-size: 9px; gap: 8px; color: var(--text-color-lighter); padding: 10px 3px 0; }.typing-indicator { padding: 8px 0; }.typing-indicator span { background: var(--primary-color); height: 6px; width: 6px; }
.message-content :deep(pre) { border: 1px solid var(--border-color); border-radius: 8px; background: var(--background-color); padding: 16px; margin: 14px 0; }.message-content :deep(code) { background: var(--background-color); font-size: 12px; }.message-content :deep(pre code) { padding: 0; background: none; }.message-content :deep(a) { color: var(--primary-color); text-decoration: underline; }.message-content :deep(blockquote) { border-left: 3px solid var(--primary-color); margin: 14px 0; padding-left: 14px; color: var(--text-color-light); }.message-content :deep(table) { border-collapse: collapse; max-width: 100%; display: block; overflow: auto; margin: 14px 0; }.message-content :deep(td), .message-content :deep(th) { border: 1px solid var(--border-color); padding: 8px 12px; }.message-content :deep(h1), .message-content :deep(h2), .message-content :deep(h3) { font-size: 1.15em; margin: 18px 0 10px; }
@media (max-width: 1150px) { .ai-chat-container { padding: 24px; }.messages-container { padding: 23px; } }
@media (max-width: 899px) { .ai-chat-container { padding: 20px 15px calc(82px + env(safe-area-inset-bottom)); }.chat-page-header { margin-bottom: 17px; }.chat-page-header h1 { font-size: 21px; }.chat-content { border-radius: 12px; }.composer-hint > span:first-child { display: none; }.composer-hint { justify-content: center; }.composer-wrap { padding: 10px 14px 12px; }.chat-toolbar { padding: 13px 17px; } }
@media (max-width: 480px) { .ai-chat-container { padding: 15px 10px calc(79px + env(safe-area-inset-bottom)); }.chat-page-header { padding: 0 7px; }.chat-page-header .eyebrow { font-size: 7px; }.quiet-button { font-size: 11px; padding: 9px 11px; }.messages-container { padding: 20px 15px; }.user-message { max-width: 92%; } }

</style>
