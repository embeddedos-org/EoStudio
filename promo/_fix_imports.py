import os

base = '/home/spatchava/embeddedos-org/eostudio-promo-video/src'

index_content = (
    'import { registerRoot } from "remotion";\n'
    'import { RemotionRoot } from "./Root.jsx";\n'
    'registerRoot(RemotionRoot);\n'
)

root_content = (
    'import { Composition } from "remotion";\n'
    'import { EoStudioPromo } from "./EoStudioPromo.jsx";\n'
    '\n'
    'export const RemotionRoot = () => {\n'
    '  return (\n'
    '    <Composition\n'
    '      id="EoStudioPromo"\n'
    '      component={EoStudioPromo}\n'
    '      durationInFrames={450}\n'
    '      fps={30}\n'
    '      width={1920}\n'
    '      height={1080}\n'
    '    />\n'
    '  );\n'
    '};\n'
)

with open(f'{base}/index.js', 'w') as f:
    f.write(index_content)

with open(f'{base}/Root.jsx', 'w') as f:
    f.write(root_content)

print('Fixed imports with .jsx extensions')
for fn in os.listdir(base):
    fpath = os.path.join(base, fn)
    print(f'  {fn}: {os.path.getsize(fpath)} bytes')
    if fn in ('index.js', 'Root.jsx'):
        with open(fpath) as rf:
            print(f'    Content: {rf.read()[:120]}...')
