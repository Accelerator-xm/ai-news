<template>
  <div class="app" :class="{ 'auth-layout': isAuth }">
    <app-sidebar v-if="!isAuth" />
    <main class="app-stage">
    <router-view v-slot="{ Component }">
      <template v-if="$route.meta.keepAlive">
        <keep-alive>
          <component :is="Component" />
        </keep-alive>
      </template>
      <template v-else>
        <component :is="Component" />
      </template>
    </router-view>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from './components/AppSidebar.vue'
const route = useRoute()
const isAuth = computed(() => ['/login', '/register'].includes(route.path))
// App.vue 作为根组件
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
    Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-size: 16px;
  background-color: var(--background-color);
  color: var(--text-color);
  height: 100%;
  width: 100%;
}

.app {
  max-width: none;
  margin: 0 auto;
  min-height: 100%;
}

/* 移动端适配 */
@media screen and (max-width: 750px) {
  html {
    font-size: 16px;
  }
}
</style>
