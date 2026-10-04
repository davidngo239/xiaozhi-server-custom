import { beforeEach, describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { localizeSystemText } from '../src/i18n/systemText';

describe('Vietnamese system labels', () => {
  it('translates provider fields and names without changing protocol identifiers or configuration', () => {
    const field = { key: 'access_token', label: '访问令牌', default: 'credential-value' };
    const original = JSON.stringify(field);
    expect(localizeSystemText(field.label)).toBe('Token truy cập');
    expect(localizeSystemText('火山引擎语音识别(流式)')).toBe('Nhận dạng giọng nói liên tục Volcengine');
    expect(localizeSystemText('获取模型配置失败')).toBe('Không thể lấy cấu hình mô hình');
    expect(JSON.stringify(field)).toBe(original);
    expect(localizeSystemText(field.key)).toBe('access_token');
    expect(localizeSystemText(field.default)).toBe('credential-value');
  });

  it('preserves user content, unknown labels and other language selections', () => {
    expect(localizeSystemText('用户自己写的内容')).toBe('用户自己写的内容');
    expect(localizeSystemText('API密钥', 'en')).toBe('API密钥');
    expect(localizeSystemText(null)).toBeNull();
    expect(localizeSystemText(42)).toBe(42);
  });
});

describe('Vietnamese default in browsers with existing settings', () => {
  beforeEach(() => localStorage.clear());
  const source = readFileSync('src/i18n/index.js', 'utf8');
  const resolver = source.slice(source.indexOf('const getDefaultLanguage'), source.indexOf('const i18n ='));
  function resolve() {
    return vm.runInNewContext(`${resolver}\ngetDefaultLanguage();`, { localStorage });
  }

  it('migrates a previously saved Chinese locale without clearing login or account data', () => {
    localStorage.setItem('userLanguage', 'zh_CN');
    localStorage.setItem('token', 'existing-login-token');
    expect(resolve()).toBe('vi');
    expect(localStorage.getItem('userLanguage')).toBe('vi');
    expect(localStorage.getItem('token')).toBe('existing-login-token');
  });

  it('preserves a subsequent explicit language selection', () => {
    expect(resolve()).toBe('vi');
    localStorage.setItem('userLanguage', 'en');
    expect(resolve()).toBe('en');
  });
});

describe('Vietnamese legal pages', () => {
  it.each(['login', 'register', 'retrievePassword'])('%s opens the Vietnamese documents', (view) => {
    const source = readFileSync(`src/views/${view}.vue`, 'utf8');
    const body = source.match(/openPage\(url\)\s*\{([\s\S]*?)\n    \},/)[1];
    const calls = [];
    const open = vm.runInNewContext(`(function(url) {${body}})`, {
      window: { open: (...args) => calls.push(args) },
    });
    open.call({ $i18n: { locale: 'vi' } }, '/user-agreement.html');
    open.call({ $i18n: { locale: 'vi' } }, '/privacy-policy.html');
    expect(calls).toEqual([
      ['/user-agreement-vi.html', '_blank'],
      ['/privacy-policy-vi.html', '_blank'],
    ]);
    for (const document of ['user-agreement', 'privacy-policy']) {
      const html = readFileSync(`public/${document}-vi.html`, 'utf8');
      expect(html).toContain('lang="vi"');
      expect(html.replace(/<!--[\s\S]*?-->/g, '')).not.toMatch(/[\u3400-\u9fff]/);
    }
  });
});
