const { defineConfig } = require('@vue/cli-service');
const dotenv = require('dotenv');
// TerserPlugin để thu nhỏ JavaScript
const TerserPlugin = require('terser-webpack-plugin');
// CompressionPlugin bật tính năng nén Gzip
const CompressionPlugin = require('compression-webpack-plugin')
// BundleAnalyzerPlugin được sử dụng để phân tích các tệp được đóng gói
const BundleAnalyzerPlugin = require('webpack-bundle-analyzer').BundleAnalyzerPlugin;
// WorkboxPlugin được sử dụng để tạo Service Worker
const { InjectManifest } = require('workbox-webpack-plugin');
// Giới thiệu module đường dẫn

const path = require('path')

function resolve(dir) {
  return path.join(__dirname, dir)
}

// Đảm bảo tệp .env đã được tải
dotenv.config();

// Xác định danh sách tài nguyên CDN để đảm bảo Service Worker cũng có thể truy cập nó
const cdnResources = {
  css: [
    'https://unpkg.com/element-ui@2.15.14/lib/theme-chalk/index.css',
    'https://cdnjs.cloudflare.com/ajax/libs/normalize/8.0.1/normalize.min.css'
  ],
  js: [
    'https://unpkg.com/vue@2.6.14/dist/vue.min.js',
    'https://unpkg.com/vue-router@3.6.5/dist/vue-router.min.js',
    'https://unpkg.com/vuex@3.6.2/dist/vuex.min.js',
    'https://unpkg.com/element-ui@2.15.14/lib/index.js',
    'https://unpkg.com/axios@0.27.2/dist/axios.min.js',
    'https://unpkg.com/opus-decoder@0.7.7/dist/opus-decoder.min.js'
  ]
};

// Xác định có nên sử dụng CDN hay không
const useCDN = process.env.VUE_APP_USE_CDN === 'true';

module.exports = defineConfig({
  productionSourceMap: process.env.NODE_ENV !== 'production', // Môi trường sản xuất không tạo ra bản đồ nguồn
  devServer: {
    port: 8001, // Cổng được chỉ định là 8001
    proxy: {
      '/xiaozhi': {
        target: 'http://127.0.0.1:8002',
        changeOrigin: true
      }
    },
    client: {
      overlay: false, // Không hiển thị lớp phủ lỗi webpack
    },
  },
  publicPath: process.env.VUE_APP_PUBLIC_PATH || "/",
  chainWebpack: config => {

    // Sửa đổi cấu hình trình cắm HTML và chèn động các liên kết CDN
    config.plugin('html')
      .tap(args => {
        // Quyết định có nên sử dụng CDN hay không dựa trên cấu hình
        if (process.env.NODE_ENV === 'production' && useCDN) {
          args[0].cdn = cdnResources;
        }
        return args;
      });

    // Tối ưu hóa việc tách mã
    config.optimization.splitChunks({
      chunks: 'all',
      minSize: 20000,
      maxSize: 250000,
      cacheGroups: {
        vendors: {
          name: 'chunk-vendors',
          test: /[\\/]node_modules[\\/]/,
          priority: -10,
          chunks: 'initial',
        },
        common: {
          name: 'chunk-common',
          minChunks: 2,
          priority: -20,
          chunks: 'initial',
          reuseExistingChunk: true,
        },
      }
    });

    // Bật cài đặt tối ưu hóa
    config.optimization.usedExports(true);
    config.optimization.concatenateModules(true);
    config.optimization.minimize(true);
  },
  configureWebpack: config => {
    if (process.env.NODE_ENV === 'production') {
      // Kích hoạt tính năng biên dịch đa luồng
      config.optimization = {
        minimize: true,
        minimizer: [
          new TerserPlugin({
            parallel: true,
            terserOptions: {
              compress: {
                drop_console: true,
                drop_debugger: true,
                pure_funcs: ['console.log']
              }
            }
          })
        ]
      };
      config.plugins.push(
        new CompressionPlugin({
          algorithm: 'gzip',
          test: /\.(js|css|html|svg)$/,
          threshold: 20480,
          minRatio: 0.8
        })
      );

      // Quyết định có thêm Nhân viên dịch vụ hay không dựa trên việc có sử dụng CDN hay không
      config.plugins.push(
        new InjectManifest({
          swSrc: path.resolve(__dirname, 'src/service-worker.js'),
          swDest: 'service-worker.js',
          exclude: [/\.map$/, /asset-manifest\.json$/],
          maximumFileSizeToCacheInBytes: 5 * 1024 * 1024, // 5MB
          // Điểm tiêm nhân viên dịch vụ tùy chỉnh
          injectionPoint: 'self.__WB_MANIFEST',
          // Thêm thông tin bổ sung để chuyển cho nhân viên dịch vụ
          additionalManifestEntries: useCDN ?
            [{ url: 'cdn-mode', revision: 'enabled' }] :
            [{ url: 'cdn-mode', revision: 'disabled' }]
        })
      );

      // Nếu sử dụng CDN, hãy định cấu hình các phần bên ngoài để loại trừ các gói phụ thuộc
      if (useCDN) {
        config.externals = {
          'vue': 'Vue',
          'vue-router': 'VueRouter',
          'vuex': 'Vuex',
          'element-ui': 'ELEMENT',
          'axios': 'axios',
          'opus-decoder': 'OpusDecoder'
        };
      } else {
        // Đảm bảo bạn không đặt phần bên ngoài khi không sử dụng CDN và để webpack đóng gói tất cả các phần phụ thuộc.
        config.externals = {};
      }

      if (process.env.ANALYZE === 'true') {  // Kiểm soát bởi các biến môi trường
        config.plugins.push(
          new BundleAnalyzerPlugin({
            analyzerMode: 'server',    // Kích hoạt chế độ máy chủ cục bộ
            openAnalyzer: true,        // Tự động mở trình duyệt
            analyzerPort: 8888         // Chỉ định số cổng
          })
        );
      }
      config.cache = {
        type: 'filesystem',  // Sử dụng bộ đệm hệ thống tập tin
        cacheDirectory: path.resolve(__dirname, '.webpack_cache'),  // Thư mục bộ đệm tùy chỉnh
        allowCollectingMemory: true,  // Kích hoạt tính năng thu thập bộ nhớ
        compression: 'gzip',  // Kích hoạt bộ nhớ đệm nén gzip
        maxAge: 5184000000, // Bộ đệm có hiệu lực trong 1 tháng
        buildDependencies: {
          config: [__filename]  // Bộ đệm bị vô hiệu mỗi khi tệp cấu hình được sửa đổi.
        }
      };
    }
  },
  // Hiển thị thông tin tài nguyên CDN cho service-worker.js
  pwa: {
    workboxOptions: {
      skipWaiting: true,
      clientsClaim: true
    }
  }
});
