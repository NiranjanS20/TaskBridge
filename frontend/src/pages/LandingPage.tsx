import { useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';

const FEATURES = [
  { icon: 'speed', title: 'Real-Time Allocation', desc: 'Continuous recomputation ensures the best match is always active, not just at request time.' },
  { icon: 'psychology', title: 'AI Decision Engine', desc: 'Multi-factor VAS scoring combines skill, proximity, reliability, and urgency into one optimal decision.' },
  { icon: 'hub', title: '5D Intelligent Matching', desc: 'Five-dimensional optimization across skill, location, availability, fatigue, and crisis velocity.' },
  { icon: 'crisis_alert', title: 'Predictive Crisis Detection', desc: 'Forecasts regional crisis escalation and pre-positions volunteers before demand spikes.' },
  { icon: 'balance', title: 'Fairness & Burnout Prevention', desc: 'Gini-coefficient workload balancing and automatic rest rotation protect volunteer wellbeing.' },
  { icon: 'verified', title: 'Explainable AI', desc: 'Every allocation decision comes with a full audit trail showing exactly why and how.' },
];

const USPS = [
  { icon: 'auto_awesome', text: 'Not just matching \u2014 real-time decision intelligence' },
  { icon: 'local_taxi', text: 'Uber-like dynamic allocation system for NGOs' },
  { icon: 'visibility', text: 'Explainable AI for trust and transparency' },
  { icon: 'rocket_launch', text: 'Crisis-ready, not spreadsheet-based' },
  { icon: 'favorite', text: 'Smart workload balancing for volunteers' },
];

const PIPELINE = [
  { icon: 'upload_file', label: 'Data Ingestion', color: 'bg-primary' },
  { icon: 'smart_toy', label: 'AI Processing', color: 'bg-primary-container' },
  { icon: 'calculate', label: 'VAS Scoring', color: 'bg-secondary' },
  { icon: 'hub', label: 'Matching', color: 'bg-tertiary' },
  { icon: 'assignment_turned_in', label: 'Allocation', color: 'bg-primary' },
];

export function LandingPage() {
  const navigate = useNavigate();

  const scrollToSection = (id: string) => {
    const section = document.getElementById(id);
    if (section) {
      section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <div className="min-h-screen bg-background overflow-x-hidden">
      {/* === NAVBAR === */}
      <nav className="fixed top-0 w-full z-50 glass-panel border-b border-outline-variant/20">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-primary text-on-primary flex items-center justify-center font-bold text-lg">T</div>
            <span className="text-xl font-bold tracking-tighter text-primary">TASKBRIDGE</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-on-surface-variant">
            <button type="button" onClick={() => scrollToSection('features')} className="hover:text-primary transition-colors">Features</button>
            <button type="button" onClick={() => scrollToSection('how')} className="hover:text-primary transition-colors">How It Works</button>
            <button type="button" onClick={() => scrollToSection('why')} className="hover:text-primary transition-colors">Why Us</button>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/login')} className="px-4 py-2 text-sm font-semibold text-primary hover:bg-primary-fixed rounded-lg transition-all">
              Sign In
            </button>
            <button onClick={() => navigate('/register')} className="px-4 py-2 text-sm font-semibold bg-primary text-on-primary rounded-lg hover:opacity-90 shadow-[0_4px_16px_rgba(0,60,157,0.25)] transition-all active:scale-95">
              Get Started
            </button>
          </div>
        </div>
      </nav>

      {/* === HERO === */}
      <section className="relative pt-32 pb-20 px-6">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-20 -left-32 w-96 h-96 bg-primary-fixed-dim/20 rounded-full blur-3xl" />
          <div className="absolute bottom-10 -right-32 w-80 h-80 bg-tertiary-fixed/15 rounded-full blur-3xl" />
        </div>

        <div className="max-w-4xl mx-auto text-center relative z-10">
          <div className="inline-flex items-center gap-2 bg-primary-fixed/60 text-primary px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest mb-8">
            <span className="material-symbols-outlined text-[14px]">auto_awesome</span>
            AI-Powered NGO Decision Engine
          </div>

          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight text-on-surface leading-[1.1] mb-6">
            TASKBRIDGE Volunteer<br />
            <span className="bg-gradient-to-r from-primary to-primary-container bg-clip-text text-transparent">Allocation Engine</span>
          </h1>
          <p className="text-lg md:text-xl text-on-surface-variant max-w-2xl mx-auto mb-10 leading-relaxed">
            Real-time decision intelligence for NGOs. Match the right volunteer to the right crisis in milliseconds, not hours.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button onClick={() => navigate('/register')} className="px-8 py-3.5 bg-gradient-to-r from-primary to-primary-container text-on-primary rounded-lg font-bold text-base shadow-[0_8px_32px_rgba(0,60,157,0.3)] hover:opacity-90 transition-all active:scale-95 flex items-center gap-2">
              <span className="material-symbols-outlined text-[20px]">rocket_launch</span>
              Get Started Free
            </button>
            <button onClick={() => navigate('/login')} className="px-8 py-3.5 bg-surface-container-lowest border border-outline-variant/40 text-on-surface rounded-lg font-bold text-base hover:bg-surface-container-high transition-all flex items-center gap-2">
              <span className="material-symbols-outlined text-[20px]">login</span>
              Sign In
            </button>
          </div>
        </div>
      </section>

      {/* === HOW IT WORKS === */}
      <section id="how" className="py-20 px-6 bg-surface-container-low/50">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-14">
            <p className="text-xs uppercase tracking-[0.15em] font-bold text-primary mb-2">Pipeline</p>
            <h2 className="text-3xl md:text-4xl font-extrabold text-on-surface">How It Works</h2>
          </div>
          <div className="flex flex-col md:flex-row items-center justify-between gap-2">
            {PIPELINE.map((step, i) => (
              <div key={step.label} className="flex items-center gap-2">
                <div className="flex flex-col items-center gap-3 min-w-[120px]">
                  <div className={cn("w-16 h-16 rounded-xl flex items-center justify-center text-on-primary shadow-lg", step.color)}>
                    <span className="material-symbols-outlined text-[28px]">{step.icon}</span>
                  </div>
                  <span className="text-sm font-bold text-on-surface text-center">{step.label}</span>
                </div>
                {i < PIPELINE.length - 1 && (
                  <span className="material-symbols-outlined text-outline-variant text-[24px] hidden md:block mx-1">arrow_forward</span>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* === FEATURES === */}
      <section id="features" className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-14">
            <p className="text-xs uppercase tracking-[0.15em] font-bold text-primary mb-2">Capabilities</p>
            <h2 className="text-3xl md:text-4xl font-extrabold text-on-surface">Core Features</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map((f) => (
              <div key={f.title} className="bg-surface-container-lowest rounded-xl p-6 ambient-shadow hover:-translate-y-1 hover:shadow-[0_20px_40px_-12px_rgba(0,0,0,0.1)] transition-all duration-300">
                <div className="w-12 h-12 rounded-lg bg-primary-fixed flex items-center justify-center mb-4">
                  <span className="material-symbols-outlined text-primary text-[24px]">{f.icon}</span>
                </div>
                <h3 className="text-lg font-bold text-on-surface mb-2">{f.title}</h3>
                <p className="text-sm text-on-surface-variant leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* === WHY CHOOSE US === */}
      <section id="why" className="py-20 px-6 bg-inverse-surface text-inverse-on-surface">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-14">
            <p className="text-xs uppercase tracking-[0.15em] font-bold text-primary-fixed-dim mb-2">USP</p>
            <h2 className="text-3xl md:text-4xl font-extrabold">Why Choose TASKBRIDGE</h2>
          </div>
          <div className="space-y-6">
            {USPS.map((u) => (
              <div key={u.text} className="flex items-center gap-4 bg-white/5 border border-white/10 rounded-xl px-6 py-4 hover:bg-white/10 transition-colors">
                <span className="material-symbols-outlined text-primary-fixed-dim text-[28px]">{u.icon}</span>
                <p className="text-lg font-medium">{u.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* === ROLE-BASED ENTRY === */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-xs uppercase tracking-[0.15em] font-bold text-primary mb-2">Access</p>
          <h2 className="text-3xl md:text-4xl font-extrabold text-on-surface mb-10">Choose Your Role</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { role: 'Volunteer', icon: 'volunteer_activism', desc: 'Accept tasks, track assignments, manage availability', color: 'bg-tertiary', textColor: 'text-tertiary' },
              { role: 'NGO Manager', icon: 'business_center', desc: 'Create tasks, monitor allocations, view analytics', color: 'bg-primary', textColor: 'text-primary' },
              { role: 'Admin', icon: 'admin_panel_settings', desc: 'Full system access, override allocations, configure', color: 'bg-secondary', textColor: 'text-secondary' },
            ].map((r) => (
              <div key={r.role} className="bg-surface-container-lowest rounded-xl p-8 ambient-shadow hover:-translate-y-1 hover:shadow-[0_20px_40px_-12px_rgba(0,0,0,0.1)] transition-all duration-300 flex flex-col items-center gap-4">
                <div className={cn("w-16 h-16 rounded-xl flex items-center justify-center text-on-primary", r.color)}>
                  <span className="material-symbols-outlined text-[32px]">{r.icon}</span>
                </div>
                <h3 className="text-xl font-bold text-on-surface">{r.role}</h3>
                <p className="text-sm text-on-surface-variant text-center leading-relaxed">{r.desc}</p>
                <button onClick={() => navigate('/login')} className={cn("mt-auto w-full py-2.5 rounded-lg font-bold text-sm border transition-all hover:opacity-80", `border-current ${r.textColor}`)}>
                  Login as {r.role}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* === FOOTER === */}
      <footer className="bg-surface-container-low border-t border-outline-variant/20 py-10 px-6">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-primary text-on-primary flex items-center justify-center font-bold text-xs">T</div>
            <span className="font-bold text-primary">TASKBRIDGE</span>
            <span className="text-xs text-on-surface-variant ml-2">AI-Powered Volunteer Allocation Engine</span>
          </div>
          <p className="text-xs text-on-surface-variant">Built for NGOs that refuse to compromise on efficiency.</p>
        </div>
      </footer>
    </div>
  );
}
