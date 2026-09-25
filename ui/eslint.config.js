import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import pluginVue from 'eslint-plugin-vue'
import vueParser from 'vue-eslint-parser'
import globals from 'globals'
import prettier from 'eslint-config-prettier'

export default tseslint.config(
  // Global ignores
  { ignores: ['dist/', 'node_modules/', 'coverage/'] },

  // Browser + Node globals
  {
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
    },
  },

  // Recommended base configs
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...pluginVue.configs['flat/recommended'],

  // Vue files: vue-eslint-parser as main parser, tseslint as sub-parser
  {
    files: ['**/*.vue'],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tseslint.parser,
        sourceType: 'module',
      },
    },
  },

  // Custom rules
  {
    rules: {
      'vue/multi-word-component-names': 'off',
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_' },
      ],
    },
  },

  // Disable ESLint rules that conflict with Prettier (always last)
  prettier
)
