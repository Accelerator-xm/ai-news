<template>
  <article class="news-item" role="link" tabindex="0" @click="goToDetail" @keydown.enter="goToDetail" @keydown.space.prevent="goToDetail">
    <div class="news-content"><div class="news-kicker"><span>{{ categoryName }}</span><span class="news-kicker-dot" /> 发现新视角</div><h3 class="news-title">{{ news.title }}</h3><p class="news-desc">{{ news.description }}</p><div class="news-info"><span class="news-author">{{ news.author || '新闻头条' }}</span><span>{{ formatDate(news.publishTime) }}</span><span class="news-views"><van-icon name="eye-o" /> {{ formatViews(news.views) }}</span></div></div>
    <div class="news-image"><img v-if="news.image && !imageFailed" :src="news.image" :alt="news.title" loading="lazy" @error="imageFailed = true"><div v-else class="news-image-fallback"><van-icon name="newspaper-o" /><span>KEEP EXPLORING</span></div></div>
  </article>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useNewsStore } from '../store/modules/news'
import { useRouter } from 'vue-router'

const props = defineProps({
  news: {
    type: Object,
    required: true
  }
})

const router = useRouter()
const newsStore = useNewsStore()
const imageFailed = ref(false)
const categoryName = computed(() => newsStore.categories.find(item => item.id === (props.news.categoryId ?? props.news.category_id))?.name || '精选')
const formatDate = (value) => value ? String(value).slice(0, 10).replaceAll('-', '.') : ''
const formatViews = (value) => Number(value || 0) >= 10000 ? `${(Number(value) / 10000).toFixed(1)}万` : Number(value || 0).toLocaleString()

const goToDetail = () => {
  router.push(`/news/detail/${props.news.id}`)
}
</script>

<style scoped>
.news-item {
  display: flex;
  padding: 12px 16px;
  border-bottom: 1px solid #f2f2f2;
  background-color: #fff;
}

.news-content {
  flex: 1;
  margin-right: 12px;
  overflow: hidden;
}

.news-title {
  font-size: 16px;
  font-weight: 500;
  margin: 0 0 8px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.news-desc {
  font-size: 14px;
  color: #666;
  margin: 0 0 8px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.news-info {
  font-size: 12px;
  color: #999;
  display: flex;
}

.news-info span {
  margin-right: 10px;
}

.news-image {
  width: 110px;
  height: 80px;
  flex-shrink: 0;
}

.news-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 4px;
}

.news-item { border-bottom: 1px solid var(--border-color); padding: 26px 4px; background: transparent; gap: 21px; cursor: pointer; align-items: center; transition: transform .2s; }.news-item:last-child { border-bottom: 0; }.news-item:hover .news-title { color: var(--primary-color); }.news-item:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 3px; border-radius: 5px; }.news-content { margin-right: 0; min-width: 0; }.news-kicker { font-size: 9px; display: flex; align-items: center; gap: 7px; color: var(--text-color-lighter); margin-bottom: 10px; letter-spacing: .3px; }.news-kicker > span:first-child { color: var(--primary-color); }.news-kicker-dot { height: 2px; width: 2px; border-radius: 50%; background: #b9b6a9; }.news-title { font-size: 18px; font-weight: 650; line-height: 1.65; color: var(--text-color); margin-bottom: 8px; transition: color .2s; }.news-desc { font-size: 11px; color: var(--text-color-light); line-height: 1.8; -webkit-line-clamp: 1; margin-bottom: 15px; }.news-info { font-size: 10px; color: var(--text-color-lighter); flex-wrap: wrap; gap: 5px 12px; align-items: center; }.news-info span { margin-right: 0; }.news-author { color: var(--text-color-light); }.news-views { display: flex; align-items: center; gap: 4px; }.news-image { width: 150px; height: 113px; border-radius: 7px; overflow: hidden; background: var(--secondary-color); }.news-image img { border-radius: 7px; transition: transform .4s; }.news-item:hover .news-image img { transform: scale(1.04); }.news-image-fallback { width: 100%; height: 100%; background: var(--accent-soft); color: var(--primary-color); display: flex; gap: 10px; align-items: center; justify-content: center; flex-direction: column; }.news-image-fallback .van-icon { font-size: 30px; }.news-image-fallback span { font-size: 7px; letter-spacing: 1px; }
@media (max-width: 1150px) { .news-image { width: 122px; height: 98px; }.news-item { gap: 16px; }.news-title { font-size: 16px; } }
@media (max-width: 599px) { .news-item { gap: 13px; padding: 21px 0; }.news-image { width: 106px; height: 92px; }.news-title { font-size: 15px; line-height: 1.6; -webkit-line-clamp: 2; }.news-desc { display: none; }.news-kicker { font-size: 9px; margin-bottom: 7px; }.news-info { font-size: 10px; gap: 4px 9px; margin-top: 10px; }.news-info .news-author { max-width: 95px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.news-views { display: none; } }

</style>