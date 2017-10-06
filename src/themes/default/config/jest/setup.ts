import 'jest-preset-angular';
import './globals';

const reporters = require('jasmine-reporters');
const path = require('path');

const savePath = path.resolve(__dirname, '..', '..', '..', '..', '..', 'results', 'javascript-tests');

const reporter = new reporters.JUnitXmlReporter({ savePath, consolidateAll: false, filePrefix: 'javascript-' });

(<any>jasmine)
  .getEnv()
  .addReporter(reporter);
