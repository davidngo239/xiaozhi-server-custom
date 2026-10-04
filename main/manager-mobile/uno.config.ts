// https://www.npmjs.com/package/@uni-helper/unocss-preset-uni
import { presetUni } from '@uni-helper/unocss-preset-uni'
import {
  defineConfig,
  presetAttributify,
  presetIcons,
  transformerDirectives,
  transformerVariantGroup,
} from 'unocss'

export default defineConfig({
  presets: [
    presetUni({
      attributify: {
        // tiền tố: 'fg-', // Nếu bạn thêm tiền tố, bạn cần sử dụng tiền tố `fg-` trong mã, chẳng hạn như: <div fg-border="1px Solid #000"></div>
        prefixedOnly: true,
      },
    }),
    presetIcons({
      scale: 1.2,
      warn: true,
      extraProperties: {
        'display': 'inline-block',
        'vertical-align': 'middle',
      },
    }),
    // Hỗ trợ thuộc tính lớp css
    presetAttributify(),
  ],
  transformers: [
    // Kích hoạt chức năng chỉ thị: chủ yếu được sử dụng để hỗ trợ các chỉ thị CSS như @apply, @screen và theme()
    transformerDirectives(),
    // Bật () chức năng nhóm
    // Hỗ trợ kết hợp lớp css, ví dụ: `<div class="hover:(bg-gray-400 font-medium) font-(light mono)">test unocss</div>`
    transformerVariantGroup(),
  ],
  shortcuts: [
    {
      center: 'flex justify-center items-center',
    },
  ],
  safelist: [],
  rules: [
    [
      'p-safe',
      {
        padding:
          'env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left)',
      },
    ],
    ['pt-safe', { 'padding-top': 'env(safe-area-inset-top)' }],
    ['pb-safe', { 'padding-bottom': 'env(safe-area-inset-bottom)' }],
  ],
  theme: {
    colors: {
      /** Màu chủ đề, ví dụ sử dụng: text-primary */
      primary: 'var(--wot-color-theme,#0957DE)',
    },
    fontSize: {
      /** Cung cấp cỡ chữ nhỏ hơn, chẳng hạn như: text-2xs */
      '2xs': ['20rpx', '28rpx'],
      '3xs': ['18rpx', '26rpx'],
    },
  },
})
