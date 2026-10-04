import 'element-ui/lib/theme-chalk/index.css';
import 'normalize.css/normalize.css'; // A modern alternative to CSS resets
import Vue from 'vue';
import ElementUI from 'element-ui';
import App from './App.vue';
import router from './router';
import store from './store';
import i18n from './i18n';
import { localizeSystemText } from './i18n/systemText';
import locale from 'element-ui/lib/locale'
import './styles/global.scss';
import { register as registerServiceWorker } from './registerServiceWorker';
import featureManager from './utils/featureManager';

// Tạo một bus sự kiện để liên lạc giữa các thành phần
Vue.prototype.$eventBus = new Vue();
Vue.prototype.$systemText = value => localizeSystemText(value, i18n.locale);

Vue.use(ElementUI);
locale.i18n((key, value) => i18n.t(key, value))

Vue.config.productionTip = false

// Đăng ký nhân viên dịch vụ
registerServiceWorker();

// Tạo một phiên bản Vue
new Vue({
  router,
  store,
  i18n,
  render: function (h) { return h(App) }
}).$mount('#app')
