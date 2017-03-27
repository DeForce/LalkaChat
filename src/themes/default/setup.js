const reporters = require('jasmine-reporters');
const path = require('path');

const savePath = path.resolve(__dirname, '..', '..', '..', 'result', 'javascript-tests');

const reporter = new reporters.JUnitXmlReporter({ savePath: savePath, consolidateAll: false, filePrefix: 'javascript-' });

jasmine
    .getEnv()
    .addReporter(reporter);
