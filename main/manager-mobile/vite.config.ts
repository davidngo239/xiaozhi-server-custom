import path from 'node:path'
import process from 'node:process'
import Uni from '@dcloudio/vite-plugin-uni'
import Components from '@uni-helper/vite-plugin-uni-components'
// @see https://uni-helper.js.org/vite-plugin-uni-layouts
import UniLayouts from '@uni-helper/vite-plugin-uni-layouts'
// @see https://github.com/uni-helper/vite-plugin-uni-manifest
import UniManifest from '@uni-helper/vite-plugin-uni-manifest'
// @see https://uni-helper.js.org/vite-plugin-uni-pages
import UniPages from '@uni-helper/vite-plugin-uni-pages'
// @see https://github.com/uni-helper/vite-plugin-uni-platform
// Yêu cầu sử dụng với plugin @uni-helper/vite-plugin-uni-pages
import UniPlatform from '@uni-helper/vite-plugin-uni-platform'
/**
 * Tối ưu hóa hợp đồng phụ, gọi gói chéo không đồng bộ mô-đun, tham chiếu gói chéo không đồng bộ thành phần
 * @see https://github.com/uni-ku/bundle-optimizer
 */
import Optimization from '@uni-ku/bundle-optimizer'
import dayjs from 'dayjs'
import { visualizer } from 'rollup-plugin-visualizer'
import AutoImport from 'unplugin-auto-import/vite'
import { defineConfig, loadEnv } from 'vite'
import ViteRestart from 'vite-plugin-restart'

// https://vitejs.dev/config/
export default async ({ command, mode }) => {
  // @see https://unocss.dev/
  const UnoCSS = (await import('unocss/vite')).default
  // console.log(mode === process.env.NODE_ENV) // true

  // chế độ: phân biệt giữa môi trường sản xuất và môi trường phát triển
  console.log('command, mode -> ', command, mode)
  // Nhận khi pnpm dev:h5 => phục vụ phát triển
  // Nhận khi pnpm build:h5 => build production
  // Khi nhận được pnpm dev:mp-weixin => build Development (lưu ý sự khác biệt, lệnh là build)
  // Nhận khi pnpm build:mp-weixin => build production
  // pnpm dev:app => build Development (lưu ý sự khác biệt, lệnh là build)
  // Nhận khi pnpm build:app => build production
  // Lệnh dev và build có thể sử dụng các biến môi trường của .env.development và .env.production tương ứng

  const { UNI_PLATFORM } = process.env
  console.log('UNI_PLATFORM -> ', UNI_PLATFORM) // Tải mp-weixin, h5, ứng dụng, v.v.

  const env = loadEnv(mode, path.resolve(process.cwd(), 'env'))
  const {
    VITE_APP_PORT,
    VITE_SERVER_BASEURL,
    VITE_DELETE_CONSOLE,
    VITE_SHOW_SOURCEMAP,
    VITE_APP_PUBLIC_BASE,
    VITE_APP_PROXY,
    VITE_APP_PROXY_PREFIX,
  } = env
  console.log('环境变量 env -> ', env)

  return defineConfig({
    envDir: './env', // Thư mục env tùy chỉnh
    base: VITE_APP_PUBLIC_BASE,
    plugins: [
      UniPages({
        exclude: ['**/components/**/**.*'],
        // homePage được đặt theo type="home" của khối định tuyến của tệp vue
        // Thư mục trang là src/pages và không thể định cấu hình thư mục hợp đồng phụ trong thư mục trang.
        subPackages: ['src/pages-sub'], // Nó là một mảng. Bạn có thể định cấu hình nhiều cái, nhưng nó không thể là một thư mục trong các trang.
        dts: 'src/types/uni-pages.d.ts',
      }),
      UniLayouts(),
      UniPlatform(),
      UniManifest(),
      // UniXXX cần được giới thiệu trước Uni
      {
        // Giải quyết tạm thời lỗi biên dịch trong @dcloudio/uni-mp-compiler chính thức của dcloudio
        // Vấn đề tham khảo về github: https://github.com/dcloudio/uni-app/issues/4952
        // Plug-in tùy chỉnh sẽ vô hiệu hóa devToolsEnabled của plug-in vite:vue và nội tuyến là đúng khi biên dịch mẫu vue.
        name: 'fix-vite-plugin-vue',
        configResolved(config) {
          const plugin = config.plugins.find(p => p.name === 'vite:vue')
          if (plugin && plugin.api && plugin.api.options) {
            plugin.api.options.devToolsEnabled = false
          }
        },
      },
      UnoCSS(),
      AutoImport({
        imports: ['vue', 'uni-app'],
        dts: 'src/types/auto-import.d.ts',
        dirs: ['src/hooks'], // Tự động nhập móc
        vueTemplate: true, // default false
      }),
      // Plug-in Tối ưu hóa yêu cầu tệp page.json, do đó, nó phải được thực thi sau plug-in UniPages
      Optimization({
        enable: {
          'optimization': true,
          'async-import': true,
          'async-component': true,
        },
        dts: {
          base: 'src/types',
        },
        logger: false,
      }),

      ViteRestart({
        // Thông qua plug-in này, khi sửa đổi tệp vite.config.js, cấu hình sẽ có hiệu lực mà không cần chạy lại.
        restart: ['vite.config.js'],
      }),
      // môi trường h5 thêm BUILD_TIME và BUILD_BRANCH
      UNI_PLATFORM === 'h5' && {
        name: 'html-transform',
        transformIndexHtml(html) {
          return html.replace('%BUILD_TIME%', dayjs().format('YYYY-MM-DD HH:mm:ss'))
        },
      },
      // Plug-in phân tích gói, môi trường sản xuất h5 + chỉ bật lên
      UNI_PLATFORM === 'h5'
      && mode === 'production'
      && visualizer({
        filename: './node_modules/.cache/visualizer/stats.html',
        open: false,
        gzipSize: true,
        brotliSize: true,
      }),
      // Plugin copyNativeRes chỉ được kích hoạt trên nền tảng ứng dụng
      // UNI_PLATFORM === 'app' && copyNativeRes(),
      Components({
        extensions: ['vue'],
        deep: true, // Có quét đệ quy các thư mục con hay không,
        directoryAsNamespace: false, // Có sử dụng tên thư mục làm tiền tố không gian tên hay không. Khi đúng thì tên thành phần là tên thư mục + tên thành phần.
        dts: 'src/types/components.d.ts', // Đường dẫn tệp khai báo loại thành phần được tạo tự động (để hỗ trợ TypeScript)
      }),
      Uni(),
    ],
    define: {
      __UNI_PLATFORM__: JSON.stringify(UNI_PLATFORM),
      __VITE_APP_PROXY__: JSON.stringify(VITE_APP_PROXY),
    },
    css: {
      postcss: {
        plugins: [
          // autoprefixer({
          //   // Chỉ định trình duyệt đích
          //   overrideBrowserslist: ['> 1%', 'last 2 versions'],
          // }),
        ],
      },
    },

    resolve: {
      alias: {
        '@': path.join(process.cwd(), './src'),
        '@img': path.join(process.cwd(), './src/static/images'),
      },
    },
    server: {
      host: '0.0.0.0',
      hmr: true,
      port: Number.parseInt(VITE_APP_PORT, 10),
      // Nó chỉ có hiệu lực ở đầu H5, không có tác dụng ở đầu kia (các đầu khác sử dụng build, không phải devServer)
      proxy: JSON.parse(VITE_APP_PROXY)
        ? {
            [VITE_APP_PROXY_PREFIX]: {
              target: VITE_SERVER_BASEURL,
              changeOrigin: true,
              rewrite: path => path.replace(new RegExp(`^${VITE_APP_PROXY_PREFIX}`), ''),
            },
          }
        : undefined,
    },
    esbuild: {
      drop: VITE_DELETE_CONSOLE === 'true' ? ['console', 'debugger'] : ['debugger'],
    },
    build: {
      sourcemap: false,
      // Thuận tiện cho việc gỡ lỗi bên không phải h5
      // sơ đồ nguồn: VITE_SHOW_SOURCEMAP === 'true', // Giá trị mặc định là sai
      target: 'es6',
      // Không cần nén môi trường phát triển
      minify: mode === 'development' ? false : 'esbuild',

    },
  })
}
