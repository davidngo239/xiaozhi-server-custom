import Vue from 'vue';
import VueI18n from 'vue-i18n';
import zhCN from './zh_CN';
import zhTW from './zh_TW';
import en from './en';
import de from './de';
import vi from './vi';
import ptBR from './pt_BR';

import enLocale from 'element-ui/lib/locale/lang/en'
import zhLocale from 'element-ui/lib/locale/lang/zh-CN'
import twLocale from 'element-ui/lib/locale/lang/zh-TW'
import deLocale from 'element-ui/lib/locale/lang/de'
import viLocale from 'element-ui/lib/locale/lang/vi'
import ptBRLocale from 'element-ui/lib/locale/lang/pt-br'


Vue.use(VueI18n);

// Áp dụng tiếng Việt một lần cho cả trình duyệt đã lưu ngôn ngữ trước đây.
const getDefaultLanguage = () => {
  if (!localStorage.getItem('xiaozhi-vietnamese-default-v1')) {
    localStorage.setItem('userLanguage', 'vi');
    localStorage.setItem('xiaozhi-vietnamese-default-v1', '1');
    return 'vi';
  }
  const savedLang = localStorage.getItem('userLanguage');
  if (savedLang) {
    return savedLang;
  }
  return 'vi';
};

const i18n = new VueI18n({
  locale: getDefaultLanguage(),
  fallbackLocale: 'vi',
  messages: {
    'zh_CN': { ...zhLocale, ...zhCN },
    'zh_TW': { ...twLocale, ...zhTW },
    'en': { ...en, ...enLocale },
    'de': { ...de, ...deLocale },
    'vi': { ...vi, ...viLocale },
    'pt_BR': { ...ptBR, ...ptBRLocale }
  }
});

export default i18n;

// Cung cấp một cách để chuyển đổi ngôn ngữ
export const changeLanguage = (lang) => {
  i18n.locale = lang;
  localStorage.setItem('userLanguage', lang);
  document.documentElement.lang = lang.replace('_', '-');
  // Ngôn ngữ thành phần thông báo đã thay đổi
  Vue.prototype.$eventBus.$emit('languageChanged', lang);
};
