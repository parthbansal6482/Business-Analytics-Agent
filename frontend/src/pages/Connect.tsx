import { useEffect } from "react"
import { useNavigate } from "react-router-dom"
import ShopifyConnectCard from "../components/connect/ShopifyConnectCard"
import ManualUploadCard from "../components/connect/ManualUploadCard"
import DataSourceStatus from "../components/connect/DataSourceStatus"
import PreferenceSetup from "../components/connect/PreferenceSetup"
import { useUserStore } from "../store/useUserStore"

export default function Connect() {
    const navigate = useNavigate()
    const { dataReady, syncUploadStatus } = useUserStore()

    useEffect(() => {
        syncUploadStatus()
    }, [syncUploadStatus])

    return (
        <div className="flex-1 flex flex-col items-center w-full px-6 py-10 md:px-12">
            <div className="w-full max-w-6xl flex flex-col gap-12">
                {/* Hero */}
                <section className="flex flex-col gap-4 items-center text-center py-6">
                    <div className="w-12 h-1 bg-[#b7860b]/20 rounded-full" />
                    <h1 className="text-4xl md:text-5xl font-serif font-semibold text-[#181611] leading-tight">
                        Set Up Your Intelligence Workspace
                    </h1>
                    <p className="text-[#8a7e60] text-lg max-w-2xl font-light">
                        Connect your Shopify store or upload manual data to power your AI research agent.
                        Note: Shopify and manual uploads are mutually exclusive to ensure data consistency.
                    </p>
                </section>

                {/* Data Sources Section */}
                <section className="flex flex-col gap-8">
                    <div className="flex items-center justify-between border-b border-[#e5e2db] pb-4">
                        <h2 className="text-3xl font-serif font-bold text-[#181611]">Data Sources</h2>
                        <span className="text-sm text-[#8a7e60]">Step 1 of 2</span>
                    </div>

                    {/* Store Integration Subsection */}
                    <div className="flex flex-col gap-4">
                        <h3 className="text-xl font-serif font-semibold text-[#181611]">Store Integration</h3>
                        <ShopifyConnectCard />
                    </div>

                    {/* Divider */}
                    <div className="relative flex items-center py-2">
                        <div className="flex-1 border-t border-[#e5e2db]" />
                        <span className="px-4 text-xs uppercase tracking-widest text-[#8a7e60] bg-[#FAFAF7]">or manual upload</span>
                        <div className="flex-1 border-t border-[#e5e2db]" />
                    </div>

                    {/* Manual Data Sources Subsection */}
                    <div className="flex flex-col gap-4">
                        <h3 className="text-xl font-serif font-semibold text-[#181611]">Manual Data Sources</h3>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                            <ManualUploadCard type="catalog" />
                            <ManualUploadCard type="reviews" />
                            <ManualUploadCard type="pricing" />
                            <ManualUploadCard type="competitors" />
                        </div>
                    </div>
                </section>

                {/* Data source status */}
                <DataSourceStatus />

                {/* Preferences */}
                <section>
                    <PreferenceSetup />
                </section>

                {/* CTA */}
                <section className="py-6 flex flex-col items-center gap-4">
                    <button
                        onClick={async () => {
                            const { updatePreferences } = await import("../lib/api")
                            try {
                                await updatePreferences(useUserStore.getState().preferences)
                            } catch (e) {
                                console.error("Failed to save preferences on launch", e)
                            }
                            navigate("/dashboard")
                        }}
                        disabled={!dataReady}
                        className="w-full max-w-md bg-[#b7860b] hover:bg-[#9a7009] disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold text-lg py-4 px-8 rounded-xl shadow-lg hover:shadow-xl transition-all flex items-center justify-center gap-3"
                    >
                        <span className="material-symbols-outlined">rocket_launch</span>
                        Start Researching →
                    </button>
                    {!dataReady && (
                        <p className="text-sm text-[#8a7e60]">Connect at least one data source to continue</p>
                    )}
                    {dataReady && (
                        <p className="text-sm text-[#8a7e60]">By continuing, you agree to our data processing terms.</p>
                    )}
                </section>
            </div>
        </div>
    )
}
