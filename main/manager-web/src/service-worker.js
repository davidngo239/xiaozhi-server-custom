/* global self, workbox */

// Tùy chỉnh logic xử lý để cài đặt và kích hoạt Service Worker
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Danh sách tài nguyên CDN
const CDN_CSS = [
  'https://unpkg.com/element-ui@2.15.14/lib/theme-chalk/index.css',
  'https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css'
];

const CDN_JS = [
  'https://unpkg.com/vue@2.6.14/dist/vue.min.js',
  'https://unpkg.com/vue-router@3.6.5/dist/vue-router.min.js',
  'https://unpkg.com/vuex@3.6.2/dist/vuex.min.js',
  'https://unpkg.com/element-ui@2.15.14/lib/index.js',
  'https://unpkg.com/axios@0.27.2/dist/axios.min.js',
  'https://unpkg.com/opus-decoder@0.7.7/dist/opus-decoder.min.js'
];

// Khi Service Worker được đưa vào tệp kê khai, nó sẽ tự động được thực thi.
const manifest = self.__WB_MANIFEST || [];

// Kiểm tra xem chế độ CDN đã được bật chưa
const isCDNEnabled = manifest.some(entry => 
  entry.url === 'cdn-mode' && entry.revision === 'enabled'
);

console.log(`Service Worker 已初始化, CDN模式: ${isCDNEnabled ? 'Đã bật' : 'Đã tắt'}`);

// Chèn mã liên quan đến hộp làm việc
importScripts('https://storage.googleapis.com/workbox-cdn/releases/7.0.0/workbox-sw.js');
workbox.setConfig({ debug: false });

// Mở hộp làm việc
workbox.core.skipWaiting();
workbox.core.clientsClaim();

// Đang lưu vào bộ nhớ đệm các trang ngoại tuyến
const OFFLINE_URL = '/offline.html';
workbox.precaching.precacheAndRoute([
  { url: OFFLINE_URL, revision: null }
]);

// Thêm trình xử lý sự kiện hoàn tất cài đặt để hiển thị thông báo cài đặt trên bảng điều khiển
self.addEventListener('install', event => {
  if (isCDNEnabled) {
    console.log('Service Worker 已安装，开始缓存CDN资源');
  } else {
    console.log('Service Worker 已安装，CDN模式禁用，仅缓存本地资源');
  }
  
  // Đảm bảo các trang ngoại tuyến được lưu vào bộ nhớ đệm
  event.waitUntil(
    caches.open('offline-cache').then((cache) => {
      return cache.add(OFFLINE_URL);
    })
  );
});

// Thêm trình xử lý sự kiện kích hoạt
self.addEventListener('activate', event => {
  console.log('Service Worker 已激活，现在控制着页面');
  
  // Làm sạch bộ đệm phiên bản cũ
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.filter(cacheName => {
          // Xóa bộ nhớ đệm ngoại trừ phiên bản hiện tại
          return cacheName.startsWith('workbox-') && !workbox.core.cacheNames.runtime.includes(cacheName);
        }).map(cacheName => {
          return caches.delete(cacheName);
        })
      );
    })
  );
});

// Thêm trình chặn sự kiện tìm nạp để kiểm tra xem tài nguyên CDN có chạm vào bộ đệm không
self.addEventListener('fetch', event => {
  // Giám sát bộ đệm tài nguyên CDN chỉ được thực hiện khi bật chế độ CDN
  if (isCDNEnabled) {
    const url = new URL(event.request.url);
    
    // Đối với tài nguyên CDN, xuất thông tin về việc bộ đệm có bị tấn công hay không.
    if ([...CDN_CSS, ...CDN_JS].includes(url.href)) {
      // Không can thiệp vào quá trình tìm nạp thông thường, chỉ thêm nhật ký
      console.log(`请求CDN资源: ${url.href}`);
    }
  }
});

// Chỉ lưu trữ tài nguyên CDN ở chế độ CDN
if (isCDNEnabled) {
  // Bộ nhớ đệm tài nguyên CSS CDN
  workbox.routing.registerRoute(
    ({ url }) => CDN_CSS.includes(url.href),
    new workbox.strategies.CacheFirst({
      cacheName: 'cdn-stylesheets',
      plugins: [
        new workbox.expiration.ExpirationPlugin({
          maxAgeSeconds: 365 * 24 * 60 * 60, // Tăng bộ nhớ đệm lên 1 năm
          maxEntries: 10, // Lưu trữ tối đa 10 tệp CSS
        }),
        new workbox.cacheableResponse.CacheableResponsePlugin({
          statuses: [0, 200], // Bộ nhớ đệm phản hồi thành công
        }),
      ],
    })
  );

  // Bộ nhớ đệm tài nguyên JS của CDN
  workbox.routing.registerRoute(
    ({ url }) => CDN_JS.includes(url.href),
    new workbox.strategies.CacheFirst({
      cacheName: 'cdn-scripts',
      plugins: [
        new workbox.expiration.ExpirationPlugin({
          maxAgeSeconds: 365 * 24 * 60 * 60, // Tăng bộ nhớ đệm lên 1 năm
          maxEntries: 20, // Lưu trữ tối đa 20 tệp JS
        }),
        new workbox.cacheableResponse.CacheableResponsePlugin({
          statuses: [0, 200], // Bộ nhớ đệm phản hồi thành công
        }),
      ],
    })
  );
}

// Lưu trữ tài nguyên tĩnh cục bộ bất kể chế độ CDN có được bật hay không
workbox.routing.registerRoute(
  /\.(?:js|css|png|jpg|jpeg|svg|gif|ico|woff|woff2|eot|ttf|otf)$/,
  new workbox.strategies.StaleWhileRevalidate({
    cacheName: 'static-resources',
    plugins: [
      new workbox.expiration.ExpirationPlugin({
        maxAgeSeconds: 7 * 24 * 60 * 60, // bộ nhớ đệm 7 ngày
        maxEntries: 50, // Bộ nhớ đệm lên tới 50 tệp
      }),
    ],
  })
);

// Bộ nhớ đệm các trang HTML
workbox.routing.registerRoute(
  /\.html$/,
  new workbox.strategies.NetworkFirst({
    cacheName: 'html-cache',
    plugins: [
      new workbox.expiration.ExpirationPlugin({
        maxAgeSeconds: 1 * 24 * 60 * 60, // bộ nhớ đệm 1 ngày
        maxEntries: 10, // Lưu trữ tối đa 10 tệp HTML
      }),
    ],
  })
);

// Các trang ngoại tuyến - sử dụng quy trình xử lý đáng tin cậy hơn
workbox.routing.setCatchHandler(async ({ event }) => {
  // Trả về trang mặc định phù hợp dựa trên loại yêu cầu
  switch (event.request.destination) {
    case 'document':
      // Nếu đó là yêu cầu trang web, hãy quay lại trang ngoại tuyến
      return caches.match(OFFLINE_URL);
    default:
      // Tất cả các yêu cầu khác đều trả về lỗi
      return Response.error();
  }
}); 