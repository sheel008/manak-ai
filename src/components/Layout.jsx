import { useState } from 'react'
import Sidebar from './Sidebar'
import TopBar from './TopBar'

export default function Layout({ title, breadcrumb, children }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <div className="flex h-screen h-[100dvh] overflow-hidden bg-[#F4F3EF]">
      <Sidebar
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
      />
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <TopBar
          title={title}
          breadcrumb={breadcrumb}
          onOpenMobileMenu={() => setMobileMenuOpen(true)}
        />
        <main className="flex-1 overflow-y-auto scrollbar-page px-3.5 sm:px-6 lg:px-8 py-4 sm:py-6 lg:py-7">
          {children}
        </main>
      </div>
    </div>
  )
}

