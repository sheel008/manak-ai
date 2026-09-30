import Button from './Button'
import { useLang } from '../context/LangContext'

export default function ConfirmDialog({ title, message, onConfirm, onCancel }) {
  const { t } = useLang()
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-md shadow-modal border border-[#E4E1DA] w-full max-w-sm p-5 sm:p-6">
        <h3 className="text-base sm:text-lg font-bold text-[#1A1A1A] mb-2">{title}</h3>
        <p className="text-xs sm:text-sm text-[#5C5A55] mb-5 leading-relaxed">{message}</p>
        <div className="flex justify-end gap-2.5 sm:gap-3">
          <Button variant="secondary" onClick={onCancel} className="cursor-pointer">{t('common.cancel')}</Button>
          <Button variant="danger" onClick={onConfirm} className="cursor-pointer">{t('common.confirm')}</Button>
        </div>
      </div>
    </div>
  )
}
