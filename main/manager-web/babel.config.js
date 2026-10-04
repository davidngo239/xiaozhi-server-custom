module.exports = {
  presets: [
    ['@vue/cli-plugin-babel/preset', {
      useBuiltIns: 'usage',
      corejs: 3
    }]
  ],
  plugins: [
    '@babel/plugin-syntax-dynamic-import',  // Đảm bảo hỗ trợ nhập động (Lazy Loading)
    '@babel/plugin-transform-runtime'
  ]
}
