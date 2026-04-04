import { X } from 'lucide-react'
import { useState, useEffect } from 'react'

export default function AddProjectModal({ isOpen, onClose, onSubmit }) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    sshKey: '',
    serverIp: '',
    rootDirectory: '',
    createdAt: '',
    updatedAt: '',
  });

  useEffect(() => {
    if (isOpen) {
      const now = new Date().toISOString().slice(0, 16);
      setFormData({
        name: '',
        description: '',
        sshKey: '',
        serverIp: '',
        rootDirectory: '',
        createdAt: now,
        updatedAt: now,
      });
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="bg-white w-full max-w-xl rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        <div className="px-6 py-4 border-b border-[#E5E5E5] flex items-center justify-between sticky top-0 bg-white z-10">
          <h2 className="text-xl font-bold text-[#171717]">Add New Project</h2>
          <button onClick={onClose} className="p-1 hover:bg-[#FAFAFA] rounded-md text-[#737373] transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto flex-1 custom-scrollbar">
          <form id="add-project-form" onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-[#171717] mb-1.5">Project Name</label>
              <input required type="text" name="name" value={formData.name} onChange={handleChange} className="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg focus:outline-none focus:ring-2 focus:ring-black/5 focus:border-[#171717] transition-all bg-[#FAFAFA] placeholder:text-[#A3A3A3]" placeholder="e.g. api-gateway" />
            </div>

            <div>
              <label className="block text-sm font-medium text-[#171717] mb-1.5">Description</label>
              <textarea name="description" value={formData.description} onChange={handleChange} rows="2" className="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg focus:outline-none focus:ring-2 focus:ring-black/5 focus:border-[#171717] transition-all bg-[#FAFAFA] placeholder:text-[#A3A3A3]" placeholder="Brief description of your project" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-sm font-medium text-[#171717] mb-1.5">Server IP Address</label>
                <input required type="text" name="serverIp" value={formData.serverIp} onChange={handleChange} className="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg focus:outline-none focus:ring-2 focus:ring-black/5 focus:border-[#171717] transition-all bg-[#FAFAFA] placeholder:text-[#A3A3A3]" placeholder="192.168.1.1" />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#171717] mb-1.5">Root Directory Address</label>
                <input required type="text" name="rootDirectory" value={formData.rootDirectory} onChange={handleChange} className="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg focus:outline-none focus:ring-2 focus:ring-black/5 focus:border-[#171717] transition-all bg-[#FAFAFA] placeholder:text-[#A3A3A3]" placeholder="/var/www/html/project" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-[#171717] mb-1.5">SSH Key</label>
              <textarea required name="sshKey" value={formData.sshKey} onChange={handleChange} rows="4" className="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg focus:outline-none focus:ring-2 focus:ring-black/5 focus:border-[#171717] transition-all bg-[#FAFAFA] font-mono text-xs placeholder:text-[#A3A3A3]" placeholder="-----BEGIN OPENSSH PRIVATE KEY-----&#10;...&#10;-----END OPENSSH PRIVATE KEY-----" />
            </div>

            <div className="grid grid-cols-2 gap-5">
              <div>
                <label className="block text-sm font-medium text-[#171717] mb-1.5">Created At</label>
                <input type="datetime-local" name="createdAt" value={formData.createdAt} onChange={handleChange} className="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg focus:outline-none focus:border-[#171717] transition-all bg-[#FAFAFA] text-sm text-[#525252]" />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#171717] mb-1.5">Last Updated At</label>
                <input type="datetime-local" name="updatedAt" value={formData.updatedAt} onChange={handleChange} className="w-full px-3 py-2 border border-[#E5E5E5] rounded-lg focus:outline-none focus:border-[#171717] transition-all bg-[#FAFAFA] text-sm text-[#525252]" />
              </div>
            </div>
          </form>
        </div>

        <div className="px-6 py-4 border-t border-[#E5E5E5] bg-[#FAFAFA] flex justify-end gap-3 sticky bottom-0 z-10">
          <button type="button" onClick={onClose} className="px-4 py-2 border border-[#E5E5E5] rounded-lg text-sm font-medium text-[#171717] hover:bg-white transition-colors cursor-pointer">
            Cancel
          </button>
          <button type="submit" form="add-project-form" className="px-4 py-2 bg-[#171717] text-white rounded-lg text-sm font-medium hover:bg-black transition-colors shadow-sm cursor-pointer">
            Create Project
          </button>
        </div>
      </div>
    </div>
  )
}
