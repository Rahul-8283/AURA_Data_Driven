import assert from 'node:assert/strict';
import { test } from 'node:test';
import { parseCommand, suggestMode } from '../src/lib/chatIntent.ts';

test('a /discover command forces the mode and is removed from the text', () => {
  assert.deepEqual(parseCommand('/discover find a cobalt-free cathode'), { mode: 'discover', text: 'find a cobalt-free cathode' });
  assert.deepEqual(parseCommand('  /DISCOVER   find LFP  '), { mode: 'discover', text: 'find LFP' });
});

test('an /ask command forces the other mode', () => {
  assert.deepEqual(parseCommand('/ask what is LFP?'), { mode: 'ask', text: 'what is LFP?' });
});

test('a command with no request leaves empty text so the chat can prompt for one', () => {
  assert.deepEqual(parseCommand('/discover'), { mode: 'discover', text: '' });
});

test('text that only looks like a command is not one', () => {
  assert.deepEqual(parseCommand('/discoverx find LFP'), { mode: null, text: '/discoverx find LFP' });
  assert.deepEqual(parseCommand('what is /discover?'), { mode: null, text: 'what is /discover?' });
  assert.deepEqual(parseCommand('  plain text  '), { mode: null, text: 'plain text' });
});

test('questions suggest Ask', () => {
  for (const text of [
    'What cycle life do LFP cathodes achieve?',
    'How does Mg doping affect cathode stability?',
    'Does cobalt-free LiNiO2 stay stable at high voltage?',
    'Explain cation mixing in layered oxides',
    'LFP is cheap, right?',
  ]) {
    assert.equal(suggestMode(text), 'ask', text);
  }
});

test('design requests suggest Discover', () => {
  for (const text of [
    'Find a cobalt-free cathode with high capacity',
    'Design a sodium-ion layered oxide',
    'Explore phosphate-based cathodes with improved energy density',
    'A cathode above 250 mAh/g under $50/kg',
    'Optimize an NMC variant for cycle life',
  ]) {
    assert.equal(suggestMode(text), 'discover', text);
  }
});

test('mixed or neutral messages give no suggestion', () => {
  for (const text of [
    'Can you find a cobalt-free cathode?',
    'What is the best cathode above 250 mAh/g?',
    'LFP cathode cycle life',
    'hello',
    '',
  ]) {
    assert.equal(suggestMode(text), null, JSON.stringify(text));
  }
});
