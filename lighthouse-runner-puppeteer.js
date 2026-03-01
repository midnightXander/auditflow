const _lighthouse = require('lighthouse');
const lighthouse = (_lighthouse && (_lighthouse.lighthouse || _lighthouse.default)) || _lighthouse;
const puppeteer = require('puppeteer'); // uses downloaded Chromium
const fs = require('fs').promises;
const path = require('path');

 
 async function runLighthouseAudit(url, options = {}) {
  
  // Launch Chromium via Puppeteer (it will download a compatible browser on npm install)
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
  });

  // Extract the DevTools WebSocket endpoint port so Lighthouse can connect
  const wsEndpoint = browser.wsEndpoint(); // e.g. ws://127.0.0.1:9222/devtools/browser/....
  const port = new URL(wsEndpoint).port;

  const defaultOptions = {
    logLevel: 'info',
    output: 'json',
    onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo', 'pwa'],
    port: Number(port),
    ...options
  };
    
 
   try {
     console.log(`🔍 Starting Lighthouse audit for: ${url}`);
     const runnerResult = await lighthouse(url, defaultOptions);
 
     // The actual result from Lighthouse
     const result = runnerResult.lhr;

    // Close Puppeteer browser
    await browser.close();

     return {
       success: true,
       url: result.finalUrl,
       fetchTime: result.fetchTime,
       categories: extractCategories(result),
       audits: extractKeyAudits(result),
       metrics: extractMetrics(result),
       opportunities: extractOpportunities(result),
       diagnostics: extractDiagnostics(result),
       fullReport: result
     };
 
  } catch (error) {
    if (browser) {
      try { await browser.close(); } catch (e) {}
    }
    throw error;
  }
}

/**
 * Extract category scores from Lighthouse results
 */
function extractCategories(result) {
  const categories = {};
  
  for (const [key, category] of Object.entries(result.categories)) {
    categories[key] = {
      title: category.title,
      score: category.score ? Math.round(category.score * 100) : 0,
      description: category.description
    };
  }
  
  return categories;
}

/**
 * Extract key audits and their details
 */
function extractKeyAudits(result) {
  const keyAuditIds = [
    'first-contentful-paint',
    'largest-contentful-paint',
    'total-blocking-time',
    'cumulative-layout-shift',
    'speed-index',
    'interactive',
    'viewport',
    'document-title',
    'meta-description',
    'http-status-code',
    'is-on-https',
    'robots-txt',
    'image-alt',
    'aria-*',
    'color-contrast',
    'valid-lang',
    'canonical'
  ];

  const audits = {};
  
  for (const [id, audit] of Object.entries(result.audits)) {
    // Include all failed audits and key audits
    if (audit.score !== 1 || keyAuditIds.some(key => id.includes(key))) {
      audits[id] = {
        title: audit.title,
        description: audit.description,
        score: audit.score,
        scoreDisplayMode: audit.scoreDisplayMode,
        displayValue: audit.displayValue,
        details: audit.details
      };
    }
  }
  
  return audits;
}

/**
 * Extract Core Web Vitals and other key metrics
 */
function extractMetrics(result) {
  const metrics = {
    coreWebVitals: {},
    performance: {},
    resourceSummary: {}
  };

  // Core Web Vitals
  if (result.audits['largest-contentful-paint']) {
    metrics.coreWebVitals.lcp = {
      value: result.audits['largest-contentful-paint'].numericValue,
      displayValue: result.audits['largest-contentful-paint'].displayValue,
      score: result.audits['largest-contentful-paint'].score,
      rating: getMetricRating('lcp', result.audits['largest-contentful-paint'].numericValue)
    };
  }

  if (result.audits['cumulative-layout-shift']) {
    metrics.coreWebVitals.cls = {
      value: result.audits['cumulative-layout-shift'].numericValue,
      displayValue: result.audits['cumulative-layout-shift'].displayValue,
      score: result.audits['cumulative-layout-shift'].score,
      rating: getMetricRating('cls', result.audits['cumulative-layout-shift'].numericValue)
    };
  }

  if (result.audits['total-blocking-time']) {
    metrics.coreWebVitals.tbt = {
      value: result.audits['total-blocking-time'].numericValue,
      displayValue: result.audits['total-blocking-time'].displayValue,
      score: result.audits['total-blocking-time'].score,
      rating: getMetricRating('tbt', result.audits['total-blocking-time'].numericValue)
    };
  }

  // Other performance metrics
  if (result.audits['first-contentful-paint']) {
    metrics.performance.fcp = {
      value: result.audits['first-contentful-paint'].numericValue,
      displayValue: result.audits['first-contentful-paint'].displayValue,
      score: result.audits['first-contentful-paint'].score
    };
  }

  if (result.audits['speed-index']) {
    metrics.performance.speedIndex = {
      value: result.audits['speed-index'].numericValue,
      displayValue: result.audits['speed-index'].displayValue,
      score: result.audits['speed-index'].score
    };
  }

  if (result.audits['interactive']) {
    metrics.performance.tti = {
      value: result.audits['interactive'].numericValue,
      displayValue: result.audits['interactive'].displayValue,
      score: result.audits['interactive'].score
    };
  }

  // Resource summary
  if (result.audits['resource-summary']) {
    const items = result.audits['resource-summary'].details?.items || [];
    items.forEach(item => {
      metrics.resourceSummary[item.resourceType] = {
        count: item.requestCount,
        size: item.transferSize
      };
    });
  }

  return metrics;
}

/**
 * Get rating (good/needs-improvement/poor) for a metric
 */
function getMetricRating(metric, value) {
  const thresholds = {
    lcp: { good: 2500, poor: 4000 },
    cls: { good: 0.1, poor: 0.25 },
    tbt: { good: 200, poor: 600 },
    fcp: { good: 1800, poor: 3000 }
  };

  const threshold = thresholds[metric];
  if (!threshold) return 'unknown';

  if (value <= threshold.good) return 'good';
  if (value <= threshold.poor) return 'needs-improvement';
  return 'poor';
}

/**
 * Extract opportunities (suggestions for improvement)
 */
function extractOpportunities(result) {
  const opportunities = [];

  for (const [id, audit] of Object.entries(result.audits)) {
    if (audit.details && audit.details.type === 'opportunity' && audit.score !== 1) {
      opportunities.push({
        id,
        title: audit.title,
        description: audit.description,
        score: audit.score,
        displayValue: audit.displayValue,
        savings: {
          bytes: audit.details.overallSavingsBytes,
          ms: audit.details.overallSavingsMs
        },
        items: audit.details.items
      });
    }
  }

  // Sort by potential savings
  return opportunities.sort((a, b) => {
    const savingsA = (a.savings.ms || 0) + (a.savings.bytes || 0) / 1000;
    const savingsB = (b.savings.ms || 0) + (b.savings.bytes || 0) / 1000;
    return savingsB - savingsA;
  });
}

/**
 * Extract diagnostic information
 */
function extractDiagnostics(result) {
  const diagnostics = {
    mainThreadWork: {},
    domSize: {},
    networkRequests: {},
    javascript: {}
  };

  // Main thread work breakdown
  if (result.audits['mainthread-work-breakdown']) {
    const items = result.audits['mainthread-work-breakdown'].details?.items || [];
    diagnostics.mainThreadWork = {
      totalTime: result.audits['mainthread-work-breakdown'].displayValue,
      breakdown: items.map(item => ({
        category: item.groupLabel || item.group,
        duration: item.duration
      }))
    };
  }

  // DOM size
  if (result.audits['dom-size']) {
    const items = result.audits['dom-size'].details?.items || [];
    diagnostics.domSize = {
      total: items.find(i => i.statistic === 'Total DOM Elements')?.value,
      maxDepth: items.find(i => i.statistic === 'Maximum DOM Depth')?.value,
      maxChildren: items.find(i => i.statistic === 'Maximum Child Elements')?.value
    };
  }

  // Network requests
  if (result.audits['network-requests']) {
    const items = result.audits['network-requests'].details?.items || [];
    diagnostics.networkRequests = {
      total: items.length,
      byResourceType: {}
    };
    
    items.forEach(item => {
      const type = item.resourceType;
      if (!diagnostics.networkRequests.byResourceType[type]) {
        diagnostics.networkRequests.byResourceType[type] = 0;
      }
      diagnostics.networkRequests.byResourceType[type]++;
    });
  }

  // JavaScript execution time
  if (result.audits['bootup-time']) {
    const items = result.audits['bootup-time'].details?.items || [];
    diagnostics.javascript = {
      totalExecutionTime: result.audits['bootup-time'].displayValue,
      scripts: items.map(item => ({
        url: item.url,
        total: item.total,
        scripting: item.scripting,
        scriptParseCompile: item.scriptParseCompile
      }))
    };
  }

  return diagnostics;
}

/**
 * Save results to a JSON file
 */
async function saveResults(results, outputPath) {
  await fs.writeFile(
    outputPath,
    JSON.stringify(results, null, 2),
    'utf-8'
  );
  console.log(`✅ Results saved to: ${outputPath}`);
}

/**
 * Generate a simple HTML report
 */
function generateSimpleReport(results) {
  const categories = results.categories;
  const metrics = results.metrics;

  let html = `
<!DOCTYPE html>
<html>
<head>
  <title>Lighthouse Report - ${results.url}</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
    .header { text-align: center; margin-bottom: 40px; }
    .categories { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 40px; }
    .category { background: #f5f5f5; padding: 20px; border-radius: 8px; text-align: center; }
    .score { font-size: 48px; font-weight: bold; margin: 10px 0; }
    .score.good { color: #0cce6b; }
    .score.average { color: #ffa400; }
    .score.poor { color: #ff4e42; }
    .metrics { margin-bottom: 40px; }
    .metric { display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #ddd; }
    .opportunities { margin-bottom: 40px; }
    .opportunity { padding: 15px; background: #fff3cd; margin-bottom: 10px; border-radius: 5px; }
  </style>
</head>
<body>
  <div class="header">
    <h1>Lighthouse Report</h1>
    <p>${results.url}</p>
    <p><small>${new Date(results.fetchTime).toLocaleString()}</small></p>
  </div>

  <div class="categories">
    ${Object.entries(categories).map(([key, cat]) => `
      <div class="category">
        <h3>${cat.title}</h3>
        <div class="score ${getScoreClass(cat.score)}">${cat.score}</div>
      </div>
    `).join('')}
  </div>

  <div class="metrics">
    <h2>Core Web Vitals</h2>
    ${metrics.coreWebVitals.lcp ? `
      <div class="metric">
        <span>Largest Contentful Paint (LCP)</span>
        <span><strong>${metrics.coreWebVitals.lcp.displayValue}</strong> - ${metrics.coreWebVitals.lcp.rating}</span>
      </div>
    ` : ''}
    ${metrics.coreWebVitals.cls ? `
      <div class="metric">
        <span>Cumulative Layout Shift (CLS)</span>
        <span><strong>${metrics.coreWebVitals.cls.displayValue}</strong> - ${metrics.coreWebVitals.cls.rating}</span>
      </div>
    ` : ''}
    ${metrics.coreWebVitals.tbt ? `
      <div class="metric">
        <span>Total Blocking Time (TBT)</span>
        <span><strong>${metrics.coreWebVitals.tbt.displayValue}</strong> - ${metrics.coreWebVitals.tbt.rating}</span>
      </div>
    ` : ''}
  </div>

  <div class="opportunities">
    <h2>Opportunities for Improvement</h2>
    ${results.opportunities.slice(0, 5).map(opp => `
      <div class="opportunity">
        <h4>${opp.title}</h4>
        <p>${opp.description}</p>
        ${opp.savings.ms ? `<p><strong>Potential savings:</strong> ${Math.round(opp.savings.ms)}ms</p>` : ''}
      </div>
    `).join('')}
  </div>
</body>
</html>
  `;

  return html;
}

function getScoreClass(score) {
  if (score >= 90) return 'good';
  if (score >= 50) return 'average';
  return 'poor';
}

/**
 * Main execution function
 */
async function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    console.error('Usage: node lighthouse-runner.js <url> [output-file]');
    console.error('Example: node lighthouse-runner.js https://example.com results.json');
    process.exit(1);
  }

  const url = args[0];
  const outputFile = args[1] || `lighthouse-report-${Date.now()}.json`;
  const htmlFile = outputFile.replace('.json', '.html');

  try {
    const results = await runLighthouseAudit(url);

    // Save JSON results
    await saveResults(results, outputFile);

    // Generate and save HTML report
    const htmlReport = generateSimpleReport(results);
    await fs.writeFile(htmlFile, htmlReport, 'utf-8');
    console.log(`📄 HTML report saved to: ${htmlFile}`);

    // Print summary
    console.log('\n' + '='.repeat(60));
    console.log('LIGHTHOUSE AUDIT SUMMARY');
    console.log('='.repeat(60));
    console.log(`\nURL: ${results.url}\n`);
    
    console.log('Category Scores:');
    for (const [key, category] of Object.entries(results.categories)) {
      const emoji = category.score >= 90 ? '✅' : category.score >= 50 ? '⚠️' : '❌';
      console.log(`  ${emoji} ${category.title}: ${category.score}/100`);
    }

    console.log('\nCore Web Vitals:');
    if (results.metrics.coreWebVitals.lcp) {
      console.log(`  LCP: ${results.metrics.coreWebVitals.lcp.displayValue} (${results.metrics.coreWebVitals.lcp.rating})`);
    }
    if (results.metrics.coreWebVitals.cls) {
      console.log(`  CLS: ${results.metrics.coreWebVitals.cls.displayValue} (${results.metrics.coreWebVitals.cls.rating})`);
    }
    if (results.metrics.coreWebVitals.tbt) {
      console.log(`  TBT: ${results.metrics.coreWebVitals.tbt.displayValue} (${results.metrics.coreWebVitals.tbt.rating})`);
    }

    console.log('\nTop Opportunities:');
    results.opportunities.slice(0, 3).forEach((opp, i) => {
      console.log(`  ${i + 1}. ${opp.title}`);
      if (opp.savings.ms) {
        console.log(`     Potential savings: ${Math.round(opp.savings.ms)}ms`);
      }
    });

    console.log('\n' + '='.repeat(60) + '\n');

    process.exit(0);

  } catch (error) {
    console.error('❌ Audit failed:', error.message);
    process.exit(1);
  }
}

// Export for use as a module
module.exports = {
  runLighthouseAudit,
  extractCategories,
  extractMetrics,
  extractOpportunities,
  extractDiagnostics
};

// Run if called directly
if (require.main === module) {
  main();
}