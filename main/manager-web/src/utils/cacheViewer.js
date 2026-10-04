/**
 * Công cụ xem bộ đệm - Được sử dụng để kiểm tra xem tài nguyên CDN đã được Service Worker lưu vào bộ đệm hay chưa
 */

/**
 * Lấy tên của tất cả các bộ đệm của Service Worker
 * @returns danh sách tên bộ đệm {Promise<string[]>}
 */
export const getCacheNames = async () => {
  if (!('caches' in window)) {
    return [];
  }
  
  try {
    return await caches.keys();
  } catch (error) {
    console.error('获取缓存名称失败:', error);
    return [];
  }
};

/**
 * Nhận tất cả các URL trong bộ đệm được chỉ định
 * @param {string} cacheName tên bộ đệm
 * @returns {Promise<string[]>} danh sách URL được lưu trong bộ nhớ đệm
 */
export const getCacheUrls = async (cacheName) => {
  if (!('caches' in window)) {
    return [];
  }
  
  try {
    const cache = await caches.open(cacheName);
    const requests = await cache.keys();
    return requests.map(request => request.url);
  } catch (error) {
    console.error(`获取缓存 ${cacheName} 的URL失败:`, error);
    return [];
  }
};

/**
 * Kiểm tra xem một URL cụ thể đã được lưu vào bộ nhớ đệm chưa
 * @param {string} url URL cần kiểm tra
 * @returns {Promise<boolean>} cho dù nó đã được lưu vào bộ nhớ đệm hay chưa
 */
export const isUrlCached = async (url) => {
  if (!('caches' in window)) {
    return false;
  }
  
  try {
    const cacheNames = await getCacheNames();
    for (const cacheName of cacheNames) {
      const cache = await caches.open(cacheName);
      const match = await cache.match(url);
      if (match) {
        return true;
      }
    }
    return false;
  } catch (error) {
    console.error(`检查URL ${url} 是否缓存失败:`, error);
    return false;
  }
};

/**
 * Nhận trạng thái bộ đệm của tất cả tài nguyên CDN trên trang hiện tại
 * @returns {Promise<Object>} đối tượng trạng thái bộ đệm
 */
export const checkCdnCacheStatus = async () => {
  // Tìm tài nguyên từ bộ đệm CDN
  const cdnCaches = ['cdn-stylesheets', 'cdn-scripts'];
  const results = {
    css: [],
    js: [],
    totalCached: 0,
    totalNotCached: 0
  };
  
  for (const cacheName of cdnCaches) {
    try {
      const urls = await getCacheUrls(cacheName);
      
      // Phân biệt tài nguyên CSS và JS
      for (const url of urls) {
        if (url.endsWith('.css')) {
          results.css.push({ url, cached: true });
        } else if (url.endsWith('.js')) {
          results.js.push({ url, cached: true });
        }
        results.totalCached++;
      }
    } catch (error) {
      console.error(`获取 ${cacheName} 缓存信息失败:`, error);
    }
  }
  
  return results;
};

/**
 * Xóa tất cả bộ nhớ đệm của nhân viên dịch vụ
 * @returns {Promise<boolean>} Liệu nó có được xóa thành công hay không
 */
export const clearAllCaches = async () => {
  if (!('caches' in window)) {
    return false;
  }
  
  try {
    const cacheNames = await getCacheNames();
    for (const cacheName of cacheNames) {
      await caches.delete(cacheName);
    }
    return true;
  } catch (error) {
    console.error('清除所有缓存失败:', error);
    return false;
  }
};

/**
 * Xuất trạng thái bộ đệm ra bàn điều khiển
 */
export const logCacheStatus = async () => {
  console.group('Service Worker 缓存状态');
  
  const cacheNames = await getCacheNames();
  console.log('已发现的缓存:', cacheNames);
  
  for (const cacheName of cacheNames) {
    const urls = await getCacheUrls(cacheName);
    console.group(`缓存: ${cacheName} (${urls.length} 项)`);
    urls.forEach(url => console.log(url));
    console.groupEnd();
  }
  
  console.groupEnd();
  return cacheNames.length > 0;
}; 