/*SERP Reader with js and puppeteer - A module to fetch and parse search engine results pages (SERPs) for rank tracking purposes.*/

import puppeteer from 'puppeteer';

async function fetchSERP(keyword, engine = 'google') {
    const browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--proxy-server=http://192.168.56.1:808'] // Replace with your proxy if needed
    });
    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
    
    const searchUrl = engine === 'google' 
        ? `https://www.google.com/search?q=${encodeURIComponent(keyword)}`
        : `https://www.bing.com/search?q=${encodeURIComponent(keyword)}`;
    
    await page.goto(searchUrl, { waitUntil: 'networkidle2' });
    const content = await page.content();
    console.log(`Fetched SERP for "${keyword}" from ${engine}: `, content.substring(0, 10500)); // Log the first 10500 characters of the SERP content
    await browser.close();
    return content;
}

async function parseSERP(html, engine = 'google') {
    const results = [];
    if (engine === 'google') {
        // Updated regex for current Google markup
        const regex = /href="(\/url\?q=https?:\/\/[^"&]+)/g;
        let match;
        while ((match = regex.exec(html)) !== null) {
            const url = match[1].replace('/url?q=', '');
            if (url && !url.includes('google.com')) {
                results.push(url);
            }
        }
    } else if (engine === 'bing') {
        const regex = /<a href="(https?:\/\/[^"]+)"/g;
        let match;
        while ((match = regex.exec(html)) !== null) {
            results.push(match[1]);
        }
    }
    return results;
}

// Main execution
const serp = await fetchSERP('nike shoes');
const results = await parseSERP(serp);
console.log(results);