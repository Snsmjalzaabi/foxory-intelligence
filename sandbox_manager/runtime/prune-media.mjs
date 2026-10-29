// Trusted IMAGE BUILD helper, never an agent tool. No package operation on import.
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';

export function validatePolicy(policy) {
  if (policy?.schema_version !== 1) throw Error('Invalid worker package policy');
  for (const key of ['required_packages', 'forbidden_packages']) {
    const values = policy[key];
    if (!Array.isArray(values) || !values.length || new Set(values).size !== values.length
        || values.some(value => typeof value !== 'string' || !/^[a-z0-9][a-z0-9+.-]*$/.test(value)))
      throw Error('Invalid package names');
  }
  if (policy.required_packages.some(name => policy.forbidden_packages.includes(name)))
    throw Error('Required/forbidden package conflict');
  return policy;
}

export function validatePlan(policy, text) {
  validatePolicy(policy);
  if (/^Inst\s/m.test(text)) throw Error('Unexpected package installation/upgrade during removal');
  const removed = [...text.matchAll(/^(?:Remv|Purg)\s+([a-z0-9+.-]+)(?::[a-z0-9]+)?(?:\s|$)/gm)].map(m => m[1]);
  if (removed.some(name => policy.required_packages.includes(name)))
    throw Error('Removal would break a required Chromium package');
  if (!policy.forbidden_packages.every(name => removed.includes(name)))
    throw Error('Incomplete/unrecognized package-removal plan');
  return new Set(removed);
}

export function validateSharedLibraryNames(names) {
  // Inspect the actual merged files as well as dpkg metadata. These are the
  // reviewed FFmpeg and libsoup3 SONAMEs, not Chromium's bundled codecs.
  if (names.some(name => /^lib(?:avcodec|avfilter|avformat|avutil|postproc|swresample|swscale|soup-3\.0)\.so(?:\.|$)/.test(name)))
    throw Error('Excluded media/HTTP library remains on the merged filesystem');
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  if (process.env.FOXORY_WORKER_IMAGE_BUILD !== '1' || process.getuid() !== 0)
    throw Error('Build-only helper: explicit image-build opt-in required; never run on the host');
  const policy = validatePolicy(JSON.parse(fs.readFileSync(process.argv[2], 'utf8')));
  const env = {...process.env, LC_ALL:'C', DEBIAN_FRONTEND:'noninteractive'};
  const run = (program,args) => execFileSync(program,args,{env,encoding:'utf8',timeout:120000,maxBuffer:2000000});
  const installed = () => new Set(run('/usr/bin/dpkg-query',['-W','--showformat=${binary:Package}\t${db:Status-Status}\n'])
    .split('\n').filter(line => line.endsWith('\tinstalled')).map(line => line.split('\t')[0].split(':')[0]));
  const before = installed();
  if (!policy.required_packages.every(name => before.has(name))) throw Error('Required Chromium package missing before pruning');
  const planned = validatePlan(policy,run('/usr/bin/apt-get',['--simulate','purge','-y',...policy.forbidden_packages]));
  console.log(JSON.stringify({event:'reviewed-media-removal-plan',packages:[...planned]}));
  console.log(run('/usr/bin/apt-get',['purge','-y',...policy.forbidden_packages]));
  const after = installed();
  if (!policy.required_packages.every(name => after.has(name)) || policy.forbidden_packages.some(name => after.has(name)))
    throw Error('Worker package policy violated after pruning');
  if ([...before].some(name => !after.has(name) && !planned.has(name))) throw Error('Unexpected unplanned package removal');
  if ([...after].some(name => !before.has(name))) throw Error('Unexpected installed package after removal');
  for (const directory of ['/usr/lib/x86_64-linux-gnu','/usr/lib/aarch64-linux-gnu']) {
    if (fs.existsSync(directory)) validateSharedLibraryNames(fs.readdirSync(directory));
  }
  console.log(JSON.stringify({event:'worker-media-pruned',required_packages_retained:policy.required_packages.length,forbidden_packages_absent:policy.forbidden_packages.length}));
}
