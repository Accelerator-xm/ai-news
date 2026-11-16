import { defineStore } from 'pinia';

export const useThemeStore = defineStore('theme', {
  state: () => ({
    currentTheme: localStorage.getItem('theme') || 'light', // 默认浅色主题
    themes: {
      light: {
        name: '浅色模式',
        backgroundColor: '#f6f5f0',
        textColor: '#282e29',
        primaryColor: '#b77540',
        secondaryColor: '#eeece4',
      },
      dark: {
        name: '深色模式',
        backgroundColor: '#191e1b',
        textColor: '#f0f0e8',
        primaryColor: '#d6a366',
        secondaryColor: '#29312a',
      },
      blue: {
        name: '蓝色主题',
        backgroundColor: '#eff3f5',
        textColor: '#333333',
        primaryColor: '#4f7484',
        secondaryColor: '#e0e9ed',
      },
      green: {
        name: '绿色主题',
        backgroundColor: '#f1f5eb',
        textColor: '#333333',
        primaryColor: '#5f7952',
        secondaryColor: '#e5ebdc',
      }
    }
  }),
  
  getters: {
    getCurrentTheme: (state) => state.currentTheme,
    getThemeConfig: (state) => state.themes[state.currentTheme],
    getAllThemes: (state) => Object.keys(state.themes).map(key => ({
      id: key,
      name: state.themes[key].name,
      primaryColor: state.themes[key].primaryColor
    }))
  },
  
  actions: {
    setTheme(themeName) {
      if (this.themes[themeName]) {
        this.currentTheme = themeName;
        localStorage.setItem('theme', themeName);
        this.applyTheme();
      }
    },
    
    applyTheme() {
      const theme = this.themes[this.currentTheme];
      document.documentElement.dataset.theme = this.currentTheme;
      document.documentElement.style.setProperty('--background-color', theme.backgroundColor);
      document.documentElement.style.setProperty('--text-color', theme.textColor);
      document.documentElement.style.setProperty('--primary-color', theme.primaryColor);
      document.documentElement.style.setProperty('--secondary-color', theme.secondaryColor);
    },
    
    initTheme() {
      this.applyTheme();
    }
  }
});
