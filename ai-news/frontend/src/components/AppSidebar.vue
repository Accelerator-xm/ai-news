<template>
  <aside class="app-sidebar">
    <router-link to="/home" class="brand-lockup">
      <span class="brand-symbol">掘</span>
      <span><strong>新闻头条<span class="brand-dot">.</span></strong><small>THE DAILY PERSPECTIVE</small></span>
    </router-link>
    <div class="sidebar-section-label">探索 / EXPLORE</div>
    <nav class="sidebar-nav" aria-label="主导航">
      <router-link v-for="item in links" :key="item.path" :to="item.path" :class="{ 'is-active': active(item.path) }">
        <van-icon :name="item.icon" /><span>{{ item.label }}</span><span v-if="item.path === '/aichat'" class="ai-label">AI</span>
      </router-link>
    </nav>
    <div class="sidebar-note"><span class="note-spark">✳</span><p>随时提问，<br>探索更多可能。</p><router-link to="/aichat">和 AI 一起探索 <span>↗</span></router-link></div>
    <router-link to="/my" class="sidebar-account"><span class="account-avatar">{{ initial }}</span><span><strong>{{ userStore.userInfo?.nickname || userStore.userInfo?.username || '你的阅读空间' }}</strong><small>{{ userStore.getLoginStatus ? '收藏每一个好观点' : '登录，留住值得阅读的内容' }}</small></span><van-icon name="arrow" /></router-link>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '../store/user'

const route = useRoute()
const userStore = useUserStore()
const initial = computed(() => (userStore.userInfo?.username || '阅').slice(0, 1).toUpperCase())
const links = [
  { path: '/home', icon: 'newspaper-o', label: '今日头条' },
  { path: '/category', icon: 'apps-o', label: '探索频道' },
  { path: '/aichat', icon: 'comment-o', label: 'AI 问答' },
  { path: '/favorite', icon: 'star-o', label: '我的收藏' },
  { path: '/history', icon: 'clock-o', label: '最近读过' },
]
const active = (path) => path === '/home' ? route.path === '/home' || route.path.startsWith('/news/') : route.path === path
</script>

<style scoped>
.app-sidebar { position: fixed; inset: 0 auto 0 0; width: 238px; padding: 38px 23px 24px; background: #202622; color: #f8f7f1; display: flex; flex-direction: column; z-index: 1500; }
.brand-lockup { display: flex; align-items: center; gap: 11px; color: inherit; text-decoration: none; }
.brand-symbol { width: 39px; height: 43px; background: #e9aa59; color: #202622; display: grid; place-items: center; border-radius: 3px 12px 3px 3px; font: 800 26px serif; }
.brand-lockup strong { display: block; font-size: 21px; letter-spacing: 2px; }.brand-dot { color: #e9aa59; }
.brand-lockup small { display: block; margin-top: 5px; font-size: 7px; letter-spacing: 1.4px; color: #aeb5ad; }
.sidebar-section-label { margin: 52px 13px 15px; color: #88968a; font-size: 10px; letter-spacing: 1.8px; }
.sidebar-nav { display: flex; flex-direction: column; gap: 9px; }.sidebar-nav a { color: #b9c2ba; text-decoration: none; display: flex; align-items: center; gap: 13px; padding: 14px 15px; font-size: 14px; border-radius: 8px; transition: background .2s, color .2s; }.sidebar-nav .van-icon { font-size: 20px; }.sidebar-nav a:hover { background: #2b342d; color: white; }.sidebar-nav .is-active { color: #f4d4a5; background: #343a2f; box-shadow: inset 3px 0 #e9aa59; }
.ai-label { font: 700 9px monospace; margin-left: auto; border: 1px solid #68735e; padding: 2px 4px; border-radius: 4px; }
.sidebar-note { margin: auto 8px 30px; padding-top: 45px; }.note-spark { color: #e9aa59; font-size: 36px; }.sidebar-note p { color: #d9dfd7; font-size: 20px; line-height: 1.65; letter-spacing: 1px; margin: 12px 0 18px; }.sidebar-note a { color: #aebcae; font-size: 11px; text-decoration: none; }.sidebar-note a span { margin-left: 16px; color: #e9aa59; }
.sidebar-account { display: flex; align-items: center; gap: 10px; color: inherit; text-decoration: none; border-top: 1px solid #3a433a; padding-top: 22px; }.account-avatar { width: 36px; height: 36px; flex-shrink: 0; display: grid; place-items: center; border-radius: 50%; background: #444d3d; color: #eed4ac; font-size: 14px; }.sidebar-account strong { display: block; font-size: 12px; max-width: 125px; overflow: hidden; text-overflow: ellipsis; }.sidebar-account small { display: block; margin-top: 5px; font-size: 9px; color: #98a497; }.sidebar-account > .van-icon { margin-left: auto; font-size: 12px; color: #98a497; }
@media (max-width: 899px) { .app-sidebar { display: none; } }
</style>
