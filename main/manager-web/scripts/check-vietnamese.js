const fs = require('fs');
const path = require('path');
const parser = require('@babel/parser');
const compiler = require('vue-template-compiler');

const root = path.resolve(__dirname, '..');
const han = /[\u3400-\u9fff]/;
const problems = [];
// Các chuỗi này là so sánh với các lỗi máy chủ cũ, không phải văn bản được hiển thị.
const legacyErrorMatches = new Set(['图形验证码']);

function checkScript(source, file) {
  const ast = parser.parse(source, { sourceType: 'unambiguous', plugins: ['dynamicImport'] });
  function walk(node, diagnostics = false) {
    if (!node || typeof node !== 'object') return;
    if (node.type === 'CallExpression' && node.callee?.type === 'MemberExpression') {
      diagnostics ||= node.callee.object?.name === 'console';
    }
    const text = node.type === 'StringLiteral' ? node.value
      : node.type === 'TemplateElement' ? node.value.cooked : null;
    if (!diagnostics && text && han.test(text) && !legacyErrorMatches.has(text)) {
      problems.push(`${file}:${node.loc.start.line}: ${text.slice(0, 100)}`);
    }
    for (const [key, value] of Object.entries(node)) {
      if (['comments', 'leadingComments', 'trailingComments', 'innerComments', 'loc', 'extra'].includes(key)) continue;
      if (Array.isArray(value)) value.forEach(item => walk(item, diagnostics));
      else if (value && typeof value === 'object') walk(value, diagnostics);
    }
  }
  walk(ast);
}

function checkTemplate(source, file) {
  const ast = compiler.compile(source, { comments: false }).ast;
  function walk(node) {
    if (!node) return;
    if (node.type !== 1 && node.text && han.test(node.text)) problems.push(`${file}:template: ${node.text.trim()}`);
    for (const attr of node.attrsList || []) {
      if (han.test(attr.value)) problems.push(`${file}:template: ${attr.name}=${attr.value}`);
    }
    (node.children || []).forEach(walk);
    (node.ifConditions || []).slice(1).forEach(condition => walk(condition.block));
  }
  walk(ast);
}

function visit(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const file = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      // Danh mục ngôn ngữ nguồn và khóa tra cứu bản dịch là có chủ ý.
      if (entry.name !== 'i18n') visit(file);
      continue;
    }
    if (/\.test\./.test(entry.name)) continue;
    const source = fs.readFileSync(file, 'utf8');
    if (/\.js$/.test(file)) checkScript(source, file);
    if (/\.vue$/.test(file)) {
      const component = compiler.parseComponent(source);
      if (component.script) checkScript(component.script.content, file);
      if (component.template) checkTemplate(component.template.content, file);
    }
  }
}

visit(path.join(root, 'src'));
checkScript(fs.readFileSync(path.join(root, 'src/i18n/vi.js'), 'utf8'), 'src/i18n/vi.js');
for (const name of ['offline.html', 'user-agreement-vi.html', 'privacy-policy-vi.html', 'index.html', 'generator/index.html']) {
  const file = path.join(root, 'public', name);
  const source = fs.readFileSync(file, 'utf8').replace(/<!--[\s\S]*?-->/g, '');
  if (han.test(source)) problems.push(`${name}: contains untranslated Chinese text`);
}
// Trình tạo đi kèm có danh mục ngôn ngữ và mã khởi tạo riêng.
const generatorPath = path.join(root, 'public/generator/assets/index-Guo1hQ-y.js');
const generator = fs.readFileSync(generatorPath, 'utf8');
const generatorAst = parser.parse(generator, { sourceType: 'module' });
const declarations = new Map();
for (const statement of generatorAst.program.body) {
  if (statement.type === 'VariableDeclaration') {
    for (const declaration of statement.declarations) declarations.set(declaration.id.name, declaration.init);
  }
}
function checkGeneratorCatalog(node, key = 'generator.vi') {
  if (node?.type === 'Identifier') return checkGeneratorCatalog(declarations.get(node.name), key);
  if (node?.type === 'StringLiteral' && han.test(node.value)) problems.push(`${key}: ${node.value}`);
  if (node?.type === 'ObjectExpression') {
    for (const property of node.properties) checkGeneratorCatalog(property.value, `${key}.${property.key.name || property.key.value}`);
  }
  if (node?.type === 'ArrayExpression') node.elements.forEach((item, index) => checkGeneratorCatalog(item, `${key}.${index}`));
}
if (!declarations.has('Ad')) problems.push('Generator Vietnamese catalog not found; update the audit for the new bundle.');
else checkGeneratorCatalog(declarations.get('Ad'));
if (!generator.includes('function td(){return localStorage.getItem("user-language")||"vi"}')) {
  problems.push('Generator does not initialize with the selected language or Vietnamese default.');
}
if (problems.length) {
  console.error(problems.join('\n'));
  process.exit(1);
}
console.log('Vietnamese check passed: UI templates, runtime strings, Vietnamese catalog and public pages.');
