import { NavLink } from "react-router-dom"
import CostBadge from "../shared/CostBadge"

export default function Navbar() {
    return (
        <header className="sticky top-0 z-50 bg-white border-b border-[#e5e2db] shadow-sm">
            <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
                {/* Logo */}
                <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 bg-[#b7860b]/10 rounded-lg flex items-center justify-center text-[#b7860b]">
                        <span className="material-symbols-outlined" style={{ fontSize: 20 }}>psychology_alt</span>
                    </div>
                    <span className="text-lg font-bold font-serif text-[#181611] tracking-tight">IntelAgent</span>
                </div>

                {/* Right side */}
                <div className="flex items-center gap-6">
                    {/* Nav links */}
                    <nav className="hidden md:flex items-center gap-6">
                        <NavLink
                            to="/connect"
                            className={({ isActive }) =>
                                `text-sm font-medium transition-colors hover:text-[#b7860b] ${isActive ? "text-[#b7860b]" : "text-[#181611]"
                                }`
                            }
                        >
                            Data Sources
                        </NavLink>
                        <NavLink
                            to="/history"
                            className={({ isActive }) =>
                                `text-sm font-medium transition-colors hover:text-[#b7860b] ${isActive ? "text-[#b7860b]" : "text-[#181611]"
                                }`
                            }
                        >
                            History
                        </NavLink>
                    </nav>

                    {/* Cost badge */}
                    <CostBadge />
                </div>
            </div>
        </header>
    )
}
