<template>
  <div class="home">
    <header class="home-masthead"><span class="masthead-brand">新闻头条<span>.</span></span><span class="edition-date">{{ editionDate }}<i /> 每日新视角</span></header>
    <div class="section-heading"><div><span class="eyebrow">THE READING ROOM</span><h2>今日阅读<span> / {{ selectedCategory }}</span></h2></div><span class="edition-index">01 — EXPLORE</span></div>
    <div class="home-layout"><section class="news-feed"><div class="feed-navigation"><van-tabs v-model:active="activeTab" animated><van-tab v-for="category in displayCategories" :key="category.id" :title="getCategoryTranslation(category.name)" /></van-tabs>
      <!-- 更多选项独立div -->
      <div class="more-options"><button class="more-tab" @click="goToCategory" aria-label="查看全部频道"><van-icon name="apps-o" /></button></div></div>
      <van-pull-refresh v-model="newsStore.refreshing" @refresh="onRefresh"><van-list v-model:loading="newsStore.loading" :finished="newsStore.finished" :finished-text="$t('home.noMore')" :immediate-check="false" @load="onLoad"><news-item v-for="item in newsStore.newsList" :key="item.id" :news="item" /><div v-if="newsStore.loading && !newsStore.newsList.length" class="feed-skeleton"><div v-for="item in 3" :key="item" class="skeleton-row"><div><i class="skeleton" /><i class="skeleton" /><i class="skeleton" /></div><span class="skeleton" /></div></div><van-empty v-if="!newsStore.loading && !newsStore.newsList.length" description="这个频道暂时没有新闻，换一个看看吧" /></van-list></van-pull-refresh></section>
      <aside class="reading-rail"><section class="rail-editor-note"><span class="eyebrow">A MOMENT TO THINK</span><span class="rail-quote">“</span><h3>新闻的价值，<br>在于理解之后。</h3><p>慢一点阅读，多一点思考。<br>每个问题，都可以成为新的起点。</p><router-link to="/aichat">带着问题去探索 <span>↗</span></router-link></section><section class="rail-channels"><span class="eyebrow">FIND YOUR INTEREST</span><h3>换个频道看看</h3><button v-for="category in displayCategories.filter(item => item.id !== newsStore.currentCategory).slice(0, 4)" :key="category.id" @click="chooseCategory(category.id)"><span>{{ getCategoryTranslation(category.name) }}</span><van-icon name="arrow" /></button></section><div class="rail-footer"><span>新闻头条.</span><p>在这里，保持好奇。</p></div></aside>
    </div>
    <tab-bar />
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed, onBeforeUnmount } from 'vue'
import { useNewsStore } from '../store/modules/news'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import NewsItem from '../components/NewsItem.vue'
import TabBar from '../components/TabBar.vue'

const newsStore = useNewsStore()
const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const activeTab = ref(0)
const tabsTop = ref(0)
const showDropdown = ref(false)
const editionDate = new Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai', month: 'long', day: 'numeric', weekday: 'long' }).format(new Date())
const selectedCategory = computed(() => newsStore.categories.find(item => item.id === newsStore.currentCategory)?.name || '头条')
const chooseCategory = (id) => {
  const index = displayCategories.value.findIndex(item => item.id === id)
  if (index >= 0) activeTab.value = index
}

// 监听路由变化
watch(
  () => route.query.categoryId,
  (newCategoryId) => {
    if (newCategoryId) {
      const categoryId = parseInt(newCategoryId)
      // 找到分类ID对应的索引
      const filteredCategories = newsStore.categories.filter(category => category.name !== '更多')
      const index = filteredCategories.findIndex(cat => cat.id === categoryId)
      
      if (index !== -1) {
        // 设置activeTab为对应索引
        activeTab.value = index
        // 切换分类
        if (categoryId !== newsStore.currentCategory) newsStore.changeCategory(categoryId)
      }
    }
  },
  { immediate: true }
)

onMounted(() => {
  // 获取新闻分类
  newsStore.getCategories().then(() => {
    // 获取新闻列表
    const target = Number(route.query.categoryId) || newsStore.currentCategory
    const categoryChanged = target !== newsStore.currentCategory
    const index = displayCategories.value.findIndex(item => item.id === target)
    activeTab.value = Math.max(index, 0)
    newsStore.currentCategory = displayCategories.value[activeTab.value]?.id || target
    if (categoryChanged || (!newsStore.loading && !newsStore.newsList.length)) newsStore.getNewsList(true)
  })
  
  // 初始化位置
  setTimeout(updateTabsPosition, 300)
  
  // 添加滚动事件监听
  window.addEventListener('scroll', handleScroll)
})

// 计算属性：显示的分类（只显示非"更多"分类）
const displayCategories = computed(() => {
  // 获取所有非"更多"分类
  return newsStore.categories.filter(category => category.name !== '更多');
})

// 计算属性：更多下拉菜单中显示的分类（只显示军事、科技、财经分类）
const moreCategories = computed(() => {
  return newsStore.categories.filter(category => 
    category.name === '军事' || 
    category.name === '科技' || 
    category.name === '财经'
  );
})

// 获取分类名称的翻译
const getCategoryTranslation = (categoryName) => {
  const categoryMap = {
    '头条': 'headline',
    '社会': 'society',
    '国内': 'domestic',
    '国际': 'international',
    '娱乐': 'entertainment',
    '体育': 'sports',
    '军事': 'military',
    '科技': 'technology',
    '财经': 'finance',
    '更多': 'more'
  };
  
  const key = categoryMap[categoryName];
  return key ? t(`home.categories.${key}`) : categoryName;
}
    

// 跳转到分类页面
const goToCategory = () => {
  router.push('/category')
}

// 处理标签点击事件
const handleTabClick = (index) => {
  // 如果不是点击"更多"选项，则关闭下拉菜单
  if (displayCategories.value[index].name !== '更多') {
    showDropdown.value = false
    newsStore.changeCategory(displayCategories.value[index].id)
  }
}

// 选择更多分类中的某个分类
const selectMoreCategory = (category) => {
  showDropdown.value = false
  newsStore.changeCategory(category.id)
  
  // 找到选中分类在原始分类中的索引
  const index = newsStore.categories.findIndex(cat => cat.id === category.id)
  if (index !== -1) {
    // 直接设置activeTab为对应索引
    activeTab.value = index
  }
}
// 获取分类导航栏的位置并设置滚动监听
const updateTabsPosition = () => {
  const tabsElement = document.querySelector('.van-tabs__wrap')
  if (tabsElement) {
    tabsTop.value = tabsElement.getBoundingClientRect().top
  }
}

// 滚动事件处理
const handleScroll = () => {
  updateTabsPosition()
}

onMounted(() => {
  
  // 初始化位置
  setTimeout(updateTabsPosition, 300)
  
  // 添加滚动事件监听
  window.addEventListener('scroll', handleScroll)
})

// 组件销毁前移除事件监听
onBeforeUnmount(() => {
  window.removeEventListener('scroll', handleScroll)
})

// 监听分类变化
watch(activeTab, (newVal) => {
  const categoryId = displayCategories.value[newVal]?.id
  if (categoryId && categoryId !== newsStore.currentCategory) newsStore.changeCategory(categoryId)
})

// 下拉刷新
const onRefresh = () => {
  newsStore.getNewsList(true)
}

// 上拉加载更多
const onLoad = () => {
  if (!newsStore.categories.length) {
    newsStore.loading = false
    return
  }
  newsStore.getNewsList()
}

// 切换分类
const changeCategory = (categoryId) => {
  // 如果点击的是"更多"选项
  if (categoryId === 10) {
    goToCategory()
    return
  }
  
  newsStore.changeCategory(categoryId)
}
</script>

<style scoped>
.home {
  padding-top: 46px;
  padding-bottom: 50px;
  background-color: #f7f8fa;
  min-height: 100vh;
}

.category-tabs {
  margin-bottom: 10px;
  position: relative;
}

:deep(.van-tabs__wrap) {
  background-color: #fff;
}

:deep(.van-tab) {
  font-size: 14px;
}

:deep(.van-tab--active) {
  font-weight: bold;
  color: #1989fa;
}

.more-options {
  position: fixed;
  right: 0;
  background-color: #fff;
  padding: 0;
  border-radius: 4px 0 0 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  /* 通过计算属性动态设置top */
  top: v-bind('tabsTop + "px"');
  height: 44px; /* 与van-tabs__wrap高度一致 */
  display: flex;
  align-items: center;
}

.more-tab {
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #1989fa;
  font-weight: bold;
  height: 100%;
  padding: 0 10px;
}

.dropdown-menu {
  position: absolute;
  right: 15px;
  top: 40px;
  min-width: 100px;
  background-color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  border-radius: 4px;
  z-index: 999;
}

.dropdown-item {
  padding: 10px 15px;
  text-align: center;
  border-bottom: 1px solid #f5f5f5;
}

.dropdown-item:last-child {
  border-bottom: none;
}

.dropdown-item:hover {
  background-color: #f5f5f5;
}
</style>
