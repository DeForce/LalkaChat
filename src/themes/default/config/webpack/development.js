const path = require('path');
const merge = require('webpack-merge');
const common = require('./common');
const { AotPlugin } = require('@ngtools/webpack');

const dist = path.resolve(__dirname, '..', '..', '..', '..', '..', 'http', 'default');

const development = {
  devtool: 'cheap-inline-source-map',
  output: {
    path: dist,
    filename: './js/[name].js'
  },

  plugins: [
    new DefinePlugin({
      PRODUCTION: JSON.stringify(false)
    }),

    new AotPlugin({
      mainPath: './src/main.ts',
      skipCodeGeneration: true,
      tsConfigPath: './tsconfig.json'
    })
  ]
};

module.exports = merge(common, development);
