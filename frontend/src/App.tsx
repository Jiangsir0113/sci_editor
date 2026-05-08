import Toolbar from './components/Toolbar'
import DiffView from './components/DiffView'
import ChangeList from './components/ChangeList'
import { useEditorStore } from './store'

export default function App() {
  const { error } = useEditorStore()
  return (
    <div className="flex flex-col h-screen bg-gray-950 text-gray-100">
      <Toolbar />
      {error && (
        <div className="bg-red-900 text-red-200 px-4 py-2 text-sm">
          错误：{error}
        </div>
      )}
      <div className="flex-1 flex overflow-hidden">
        <DiffView />
      </div>
      <div className="h-64 border-t border-gray-700 overflow-y-auto">
        <ChangeList />
      </div>
    </div>
  )
}
