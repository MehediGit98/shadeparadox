"""Generate ShadeParadox figures from saved numerical results.

Uses bundled numerical results and the bundled Merriweather source font.
All inputs and the source font are bundled locally.
"""
from pathlib import Path
import argparse, io, json, os, tempfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch
from matplotlib import font_manager
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from PIL import Image

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'results'
OUT=ROOT/'reproduced'/'figures'
_FONT_TEMP=None

def register_bundled_fonts():
    """Create temporary regular/bold instances, preserving the source outlines.

    Only the original variable font is distributed. Temporary instances have
    a distinct family name to respect the source font's Reserved Font Name.
    The temporary folder remains alive while Matplotlib accesses the files.
    """
    global _FONT_TEMP
    if _FONT_TEMP is not None:
        return
    _FONT_TEMP=tempfile.TemporaryDirectory(prefix='shadeparadox_fonts_')
    for weight,style in ((400,'Regular'),(700,'Bold')):
        source=TTFont(ROOT/'fonts'/'Merriweather.ttf')
        font=instantiateVariableFont(source,{'wght':weight,'wdth':100,'opsz':18},inplace=False)
        names={1:'ShadeParadox Text',2:style,3:'ShadeParadoxText-'+style,
               4:'ShadeParadox Text '+style,6:'ShadeParadoxText-'+style,
               16:'ShadeParadox Text',17:style}
        for record in font['name'].names:
            if record.nameID in names:
                record.string=names[record.nameID].encode(record.getEncoding())
        path=Path(_FONT_TEMP.name)/('ShadeParadoxText-'+style+'.ttf')
        font.save(path)
        font_manager.fontManager.addfont(str(path))

plt.rcParams.update({'font.family':'ShadeParadox Text','font.size':8,'axes.titlesize':8,'axes.labelsize':8,
    'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'axes.spines.top':False,
    'axes.spines.right':False,'axes.linewidth':.6,'pdf.fonttype':42,'svg.fonttype':'path',
    'text.color':'#192d38','axes.labelcolor':'#192d38','xtick.color':'#192d38','ytick.color':'#192d38'})
INK='#192d38';BLUE='#327aab';TEAL='#257b74';GOLD='#bd8435';PURPLE='#86619f';PALE='#e7f0f2'
def load(s):return json.loads((DATA/s).read_text())
def export(fig,path,dpi=None):
    """Complete each image in memory, then replace the destination atomically."""
    path=Path(path)
    buffer=io.BytesIO()
    options={'format':path.suffix.lstrip('.'),'facecolor':'white'}
    if dpi is not None:
        options['dpi']=dpi
    fig.savefig(buffer,**options)
    payload=buffer.getvalue()
    if path.suffix.lower()=='.png':
        with Image.open(io.BytesIO(payload)) as im:
            im.verify()
    temp_path=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.'+path.name+'.',
                                         suffix='.tmp',delete=False) as handle:
            temp_path=Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path,path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
def save(fig,name):
    export(fig,OUT/(name+'.png'),dpi=600)
    export(fig,OUT/(name+'.svg'))
    plt.close(fig)
def arrow(ax,start,end,col=INK,lw=1,style='->'):
    ax.add_patch(FancyArrowPatch(start,end,arrowstyle=style,mutation_scale=7,lw=lw,color=col))
def common(ax):
    ax.grid(axis='x',color='#dce5e8',lw=.5);ax.set_axisbelow(True)

def geometry():
    fig=plt.figure(figsize=(6.2,3.8))
    a=fig.add_axes([.045,.2,.55,.66]);b=fig.add_axes([.66,.12,.3,.8])
    a.add_patch(Rectangle((0,0),8,3,fc='#f5f7f6',ec=INK,lw=.9))
    a.plot([0,0],[.8,2.7],color=BLUE,lw=4)
    a.plot([0,0],[1.75,2.7],color=PURPLE,lw=5)
    a.add_patch(Rectangle((1.8,.72),1.3,.08,fc=GOLD))
    a.add_patch(Circle((3.5,1.22),.15,fc=INK))
    a.plot([3.5,3.5,3.8],[1.02,.5,.15],color=INK,lw=1.7)
    a.plot([3.5,3.05],[.9,.8],color=INK,lw=1.3)
    arrow(a,(-1,2.5),(3.3,1.25),GOLD)
    arrow(a,(.15,1.5),(5,2.95),BLUE);arrow(a,(5,2.95),(3.6,1.3),BLUE)
    a.annotate('Eye 1.2 m',xy=(3.5,1.22),xytext=(4.7,.85),fontsize=8,arrowprops={'arrowstyle':'-','color':INK,'lw':.5})
    a.annotate('Shade\n50% shown',xy=(0,2.3),xytext=(.7,3.65),fontsize=8,arrowprops={'arrowstyle':'-','color':INK,'lw':.5})
    a.text(4.8,2.35,'Reflected\nlight',fontsize=8,color=BLUE)
    a.text(-1.2,3.2,'Daylight',fontsize=8,color=BLUE)
    a.annotate('Glazing\n0.8–2.7 m',xy=(0,1.0),xytext=(-1.45,-.65),fontsize=8,arrowprops={'arrowstyle':'-','color':INK,'lw':.5})
    arrow(a,(0,-.2),(8,-.2),style='<->');a.text(4,-.62,'8 m depth',ha='center')
    a.set_xlim(-1.6,8.3);a.set_ylim(-.95,4.45);a.set_aspect('equal');a.axis('off')
    a.set_title('(a) Room section',loc='left',fontweight='bold',pad=2)
    b.add_patch(Rectangle((0,0),6,8,fc='#f5f7f6',ec=INK,lw=.9))
    b.plot([.45,5.55],[0,0],color=BLUE,lw=3)
    for d in [2.5,4.5,6.5]:
        b.add_patch(Rectangle((2.1,d-.3),1.8,.6,fc='#dfc7a1'))
        b.scatter([3],[d],c=INK,s=10,zorder=5)
        arrow(b,(3,d),(4.25,d-1.25),TEAL)
        b.text(6.25,d,f'{d:.1f} m',va='center')
    b.text(3,8.5,'6 m width',ha='center');b.text(3,-.65,'Window 5.1 m',ha='center',color=BLUE)
    b.set_xlim(-.4,8.5);b.set_ylim(-1.2,9.6);b.set_aspect('equal');b.axis('off')
    b.set_title('(b) Plan and eye positions',loc='left',fontweight='bold',pad=3)
    fig.text(.04,.045,'Schematic geometry; light paths do not represent a simulated luminance image.',fontsize=8)
    save(fig,'figure_1_office_geometry')

def comparisons():
    e1=load('e1.json');keys=['always_open','glare_only','thermal_only','thermal_and_glare','illustrative_stochastic','circadian_aware']
    labels=['Always open','Glare trigger','Solar trigger','Glare or solar','Stochastic (sensitivity)','Melanopic-aware']
    fig,(a,b)=plt.subplots(2,1,figsize=(6.2,4.9));fig.subplots_adjust(left=.31,right=.97,top=.93,bottom=.19,hspace=.85)
    ys=np.arange(len(keys));vals=np.array([e1['by_controller'][k]['medi_retained']['mean'] for k in keys])*100
    lo=np.array([e1['by_controller'][k]['medi_retained']['lo'] for k in keys])*100
    hi=np.array([e1['by_controller'][k]['medi_retained']['hi'] for k in keys])*100
    bars=a.barh(ys,vals,color=TEAL,height=.62)
    bars[4].set_facecolor('#f1d8ad');bars[4].set_edgecolor(GOLD);bars[4].set_hatch('///')
    a.errorbar(vals,ys,xerr=[vals-lo,hi-vals],fmt='none',ecolor=INK,capsize=2,lw=.7)
    for yy,v in zip(ys,vals):a.text(3,yy,f'{v:.1f}%',va='center',color=INK if yy==4 else 'white')
    a.set_yticks(ys,labels);a.invert_yaxis();a.set_xlim(0,110);a.set_xlabel('Mean mEDI retained (% of always open)')
    a.set_title('(a) Continuous exposure',loc='left',fontweight='bold',pad=10);common(a)
    for off,key,col,lab in [(-.16,'dgp_delta_pp',BLUE,'DGP ≥0.35'),(.16,'compliance_delta_pp',GOLD,'mEDI ≥250 lx')]:
        v=[e1['by_controller'][k][key]['mean'] for k in keys];bars=b.barh(ys+off,v,height=.3,color=col,label=lab)
        bars[4].set_hatch('///');bars[4].set_edgecolor(INK);bars[4].set_linewidth(.3)
    b.set_yticks(ys,labels);b.invert_yaxis();b.set_xlim(-10,.6);b.set_xlabel('Change in occupied time (percentage points)')
    b.set_title('(b) Threshold-time changes',loc='left',fontweight='bold',pad=10);common(b);b.axvline(0,color=INK,lw=.6)
    fig.legend(*b.get_legend_handles_labels(),ncol=2,loc='lower center',bbox_to_anchor=(.59,.015),frameon=False)
    save(fig,'figure_2_blind_tradeoffs')

def headings():
    e3=load('e3.json');fig,(a,b)=plt.subplots(1,2,figsize=(6.2,3.35),subplot_kw={'projection':'polar'})
    fig.subplots_adjust(left=.07,right=.94,top=.77,bottom=.27,wspace=.44)
    labels={'always_open':'Always open','thermal_and_glare':'Glare or solar','illustrative_stochastic':'Illustrative stochastic','circadian_aware':'Melanopic-aware'}
    for r,c,ls,m in zip(e3['rows'],[BLUE,TEAL,GOLD,PURPLE],['-','--',':','-.'],['o','s','^','D']):
        v=sorted(r['values'],key=lambda q:q['heading_deg']);th=np.radians([q['heading_deg'] for q in v]+[v[0]['heading_deg']])
        for ax,k,scale in [(a,'medi_mean',1),(b,'mean_coverage',100)]:
            ax.plot(th,[q[k]*scale for q in v]+[v[0][k]*scale],color=c,lw=1.5,ls=ls,marker=m,ms=2.7,label=labels[r['controller']])
    for ax in (a,b):
        ax.set_theta_zero_location('N');ax.set_theta_direction(-1);ax.set_xticks(np.radians([0,90,180,270]),['0°','90°','180°','270°']);ax.grid(color='#d7e0e5',lw=.5);ax.tick_params(pad=2)
    a.set_ylim(0,4500);a.set_yticks([1000,2000,3000,4000]);a.set_rlabel_position(40)
    b.set_ylim(0,75);b.set_yticks([25,50,75],['25%','50%','75%']);b.set_rlabel_position(40)
    a.set_title('(a) Mean mEDI (lx)',pad=17,fontweight='bold');b.set_title('(b) Mean shade coverage',pad=17,fontweight='bold')
    fig.legend(*a.get_legend_handles_labels(),loc='lower center',ncol=2,frameon=False,bbox_to_anchor=(.5,.01))
    save(fig,'figure_3_view_direction')

def optimisation():
    e=load('e2.json');fig=plt.figure(figsize=(6.2,3.2));a=fig.add_axes([.27,.24,.68,.61])
    grid=np.array([[next(c['aggregates']['medi_mean'] for c in e['cells'] if c['encoding']==enc and c['optimiser']==opt) for opt in e['optimisers']] for enc in e['encodings']])
    a.imshow(grid,cmap=matplotlib.colors.ListedColormap([PALE]),aspect='auto')
    a.set_yticks(range(6),[s.replace('_',' ') for s in e['encodings']]);a.set_xticks(range(4),['Random','Latin hypercube','Coordinate','Annealing'])
    for (i,j),v in np.ndenumerate(grid):a.text(j,i,f'{v:.1f}',ha='center',va='center')
    a.set_title('(a) Mean mEDI by encoding and optimiser (lx)',loc='left',pad=10,fontweight='bold')
    a.tick_params(length=0,pad=5)
    count=len(e['cells']);distinct=len({tuple(c['outcome']) for c in e['cells']})
    state='blinds open' if all(c['aggregates']['mean_coverage']==0 for c in e['cells']) else 'shade states vary'
    algorithm=e['dispersion_from_algorithm']['mean'];encoding=e['dispersion_from_encoding']['mean']
    dispersion='Both dispersions = 0' if algorithm==encoding==0 else f'Algorithm {algorithm:.3g}; encoding {encoding:.3g}'
    fig.text(.06,.11,f'(b) All {count} selections: {state} · {distinct} outcome'+('s' if distinct!=1 else '')+f' · {dispersion}',fontsize=8)
    ratio=e['encoding_over_algorithm_ratio']['mean']
    note=('Ratio 0/0 is undefined. The default comparison cannot identify a relative effect.'
          if algorithm==encoding==0 else ('Ratio is undefined because algorithm dispersion is zero.' if ratio is None else f'Encoding / algorithm dispersion ratio: {ratio:.3g}.'))
    fig.text(.06,.035,note,fontsize=8,color='#9b433a')
    save(fig,'figure_4_unidentifiable_comparison')

def sensitivity():
    s=load('sensitivity.json');v=s['stochastic_intercept_sweep']['rows'];fig,a=plt.subplots(figsize=(6.2,3.15));fig.subplots_adjust(left=.13,right=.96,top=.86,bottom=.2)
    a.plot([r['intercept'] for r in v],[100*r['medi_retained'] for r in v],'-o',color=GOLD,ms=3,lw=1.4)
    a.axvline(-8,ls='--',color=INK,lw=.7);a.text(-7.95,94,'Default −8',va='top')
    a.set_xticks([r['intercept'] for r in v]);a.set_ylim(20,104);a.set_xlabel('Assumed stochastic closing intercept');a.set_ylabel('Mean mEDI retained (%)');a.set_title('Stochastic-rule sensitivity at fixed slope 1.6',loc='left',fontweight='bold');a.grid(color='#d7e0e5',lw=.5)
    save(fig,'figure_s1_stochastic_sensitivity')

def graphical():
    e1,e2,e3,sens=load('e1.json'),load('e2.json'),load('e3.json'),load('sensitivity.json')
    retained=[100*e1['by_controller'][k]['medi_retained']['mean'] for k in ('glare_only','thermal_only','thermal_and_glare','circadian_aware')]
    stochastic=[100*r['medi_retained'] for r in sens['stochastic_intercept_sweep']['rows']]
    heading_ratios={r['controller']:r['medi_ratio'] for r in e3['rows']}
    controlled=[v for k,v in heading_ratios.items() if k!='always_open']
    outcomes=len({tuple(c['outcome']) for c in e2['cells']})
    ratio=e2['encoding_over_algorithm_ratio']['mean']
    outcome_text='one outcome' if outcomes==1 else f'{outcomes} outcomes'
    ratio_text=('0/0 dispersion ratio is undefined' if e2['dispersion_from_algorithm']['mean']==e2['dispersion_from_encoding']['mean']==0 else ('dispersion ratio is undefined' if ratio is None else f'dispersion ratio {ratio:.3g}'))
    fig=plt.figure(figsize=(10,5),facecolor='white');a=fig.add_axes([0,0,1,1]);a.set_xlim(0,1);a.set_ylim(0,1);a.axis('off')
    a.text(.055,.92,'Blind operation and viewing direction shape melanopic exposure',fontsize=16,fontweight='bold',color=INK)
    a.text(.055,.855,f"Spectral office model · {len(e1['orientations'])} orientations · {len(e1['depths'])} depths · {len(e1['seeds'])} behavioural seeds · weighted representative days",fontsize=9)
    for x in [.345,.675]:a.plot([x,x],[.2,.76],color='#d6e1e4',lw=.7)
    a.text(.055,.745,'MODEL',fontsize=9,fontweight='bold',color=TEAL)
    a.add_patch(Rectangle((.07,.335),.24,.255,ec=INK,fc='#f4f7f7',lw=1.4))
    a.plot([.07,.07],[.395,.565],color=BLUE,lw=6);a.plot([.07,.07],[.49,.565],color=PURPLE,lw=8)
    a.add_patch(Circle((.195,.455),.013,fc=INK));a.plot([.195,.195,.222],[.435,.365,.338],color=INK,lw=2)
    a.add_patch(Rectangle((.128,.378),.065,.008,fc=GOLD))
    arrow(a,(.083,.52),(.18,.455),GOLD,lw=1.7);arrow(a,(.205,.45),(.29,.50),TEAL,lw=1.2)
    a.text(.055,.65,'6 × 8 × 3 m office\nEye at 1.2 m',fontsize=10,linespacing=1.5)
    a.text(.055,.245,'mEDI: D65-equivalent\nmelanopic exposure at the eye',fontsize=10,linespacing=1.5)
    a.text(.375,.745,'BLIND OPERATION',fontsize=9,fontweight='bold',color=TEAL)
    a.text(.375,.64,f'{min(retained):.1f}–{max(retained):.1f}%',fontsize=21,fontweight='bold',color=TEAL)
    a.text(.375,.56,'mEDI retained by trigger-based\nand melanopic-aware rules',fontsize=10,linespacing=1.4)
    a.text(.375,.435,f'{min(stochastic):.1f}–{max(stochastic):.1f}%',fontsize=21,fontweight='bold',color=GOLD)
    a.text(.375,.345,'stochastic sensitivity range\nwhen the closing intercept varies',fontsize=9,linespacing=1.4)
    a.text(.375,.245,'Assumed behaviour changes\nthe result.',fontsize=10,linespacing=1.4)
    a.text(.705,.745,'VIEWING DIRECTION',fontsize=9,fontweight='bold',color=TEAL)
    a.text(.705,.64,f"{heading_ratios['always_open']:.2f}×",fontsize=26,fontweight='bold',color=BLUE)
    a.text(.705,.56,'open-blind heading range',fontsize=10)
    a.text(.705,.435,f'{min(controlled):.2f}–{max(controlled):.2f}×',fontsize=22,fontweight='bold',color=TEAL)
    a.text(.705,.355,'under controlled rules',fontsize=10)
    a.text(.705,.26,'Specify eye direction when\nassessing melanopic exposure.',fontsize=10,linespacing=1.4)
    a.text(.055,.13,f"Optimisation diagnostic: {len(e2['cells'])} selected solutions, {outcome_text}; {ratio_text}.",fontsize=9,color=INK)
    a.text(.055,.065,'Within-model findings. Total mEDI includes electric light. No field or physiological validation is claimed.',fontsize=8,color='#566570')
    dest=OUT/'ShadeParadox_graphical_abstract.png';export(fig,dest,dpi=300);export(fig,dest.with_suffix('.svg'));plt.close(fig)


def main(study='shadeparadox',data=None,out=None):
    global DATA,OUT
    if study!='shadeparadox':
        raise ValueError('This release contains result figures for ShadeParadox only.')
    DATA=Path(data) if data is not None else ROOT/'results'
    OUT=Path(out) if out is not None else ROOT/'reproduced'/'figures'
    OUT.mkdir(parents=True,exist_ok=True)
    register_bundled_fonts()
    geometry();comparisons();headings();optimisation();sensitivity();graphical()
    print('Figures and graphical abstract written to',OUT,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,default=ROOT/'results')
    parser.add_argument('--out',type=Path,default=ROOT/'reproduced'/'figures')
    args=parser.parse_args()
    main(data=args.data,out=args.out)
