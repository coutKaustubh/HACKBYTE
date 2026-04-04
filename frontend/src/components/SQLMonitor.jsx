import { useState, useEffect } from 'react';
import { AlertCircle, RefreshCw, Database } from 'lucide-react';

const TABLES = ['incident', 'execution', 'ai_decision', 'safety_check', 'agent_event'];

export default function SQLMonitor({ projectId }) {
  const [activeTab, setActiveTab] = useState(TABLES[0]);
  const [data, setData] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const fetchProjectData = async () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    const newData = {};
    
    try {
      await Promise.all(TABLES.map(async (tableName) => {
        // Construct a filtered query if applicable
        // incident, execution, ai_decision, safety_check all have incident_id or project_id
        // agent_event has incident_id
        
        let query = `SELECT * FROM ${tableName}`;
        if (tableName === 'incident') {
          query = `SELECT * FROM incident WHERE project_id = ${projectId}`;
        } else if (['execution', 'ai_decision', 'safety_check'].includes(tableName)) {
          // Join on incident.incident_id (string), NOT incident.id (u64 PK)
          query = `SELECT t.* FROM ${tableName} t JOIN incident i ON t.incident_id = i.incident_id WHERE i.project_id = ${projectId}`;
        } else if (tableName === 'agent_event') {
          // Both sides are strings — join directly on incident.incident_id
          query = `SELECT t.* FROM agent_event t JOIN incident i ON t.incident_id = i.incident_id WHERE i.project_id = ${projectId}`;
        }

        const response = await fetch('http://127.0.0.1:3000/v1/database/realitypatch-db-2lsay/sql', {
          method: 'POST',
          headers: {
            'Content-Type': 'text/plain',
          },
          body: query
        });
        
        if (!response.ok) {
           throw new Error(`Failed to fetch ${tableName}`);
        }
        
        const json = await response.json();
        newData[tableName] = json[0] || { schema: { elements: [] }, rows: [] };
      }));
      
      setData(newData);
      setLastRefreshed(new Date());
    } catch (err) {
      console.error(err);
      setError(err.message || "An error occurred while fetching data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjectData();
  }, [projectId]);

  useEffect(() => {
    let intervalId;
    if (autoRefresh) {
      fetchProjectData();
      intervalId = setInterval(fetchProjectData, 3000);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [autoRefresh]);

  const getStatusColor = (statusValue) => {
    if (!statusValue) return '';
    const text = String(statusValue).toLowerCase();
    if (text === 'error' || text === 'failed' || text === 'blocked') return 'bg-red-100 text-red-700 border-red-200';
    if (text === 'resolved' || text === 'success' || text === 'approved') return 'bg-green-100 text-green-700 border-green-200';
    return 'bg-gray-100 text-gray-700 border-gray-200';
  };

  const currentTableData = data[activeTab];

  return (
    <div className="bg-white border border-[#E5E5E5] rounded-xl shadow-sm flex flex-col h-full overflow-hidden">
      
      {/* Header */}
      <div className="p-4 border-b border-[#E5E5E5] flex items-center justify-between bg-[#FAFAFA]">
        <div className="flex items-center gap-2">
          <Database className="w-5 h-5 text-accent" />
          <h3 className="font-bold text-[#171717]">SQL MONITOR</h3>
        </div>
        <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-[#737373]">
              <input 
                type="checkbox" 
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-[#E5E5E5] text-[#171717] focus:ring-[#171717]"
              />
              Auto-poll
            </label>
            <button 
              onClick={fetchProjectData}
              disabled={loading || autoRefresh}
              className="p-1.5 text-[#737373] hover:text-[#171717] transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex overflow-x-auto border-b border-[#E5E5E5] px-2 py-1.5 gap-1.5 bg-white">
        {TABLES.map(table => (
          <button
            key={table}
            onClick={() => setActiveTab(table)}
            className={`px-3 py-1 text-[11px] font-bold rounded transition-colors whitespace-nowrap uppercase tracking-tighter
              ${activeTab === table 
                ? 'bg-[#171717] text-white shadow-sm' 
                : 'text-[#737373] hover:text-[#171717] hover:bg-black/5'
              }`}
          >
            {table.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Table Area */}
      <div className="flex-1 overflow-auto bg-white p-0 relative min-h-[300px]">
        {error && (
          <div className="p-4 text-red-600 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}
        
        {loading && !currentTableData ? (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
            <RefreshCw className="w-6 h-6 text-[#A3A3A3] animate-spin" />
          </div>
        ) : currentTableData ? (
          currentTableData.rows.length === 0 ? (
            <div className="flex items-center justify-center h-48 text-[#A3A3A3] text-xs uppercase tracking-widest font-bold">
              Empty Set
            </div>
          ) : (
            <table className="w-full text-left border-collapse min-w-max">
              <thead className="bg-[#FAFAFA] border-b border-[#E5E5E5] sticky top-0 z-10">
                <tr>
                  {currentTableData.schema.elements.map((col, i) => (
                    <th key={i} className="px-3 py-2 text-[10px] font-bold text-[#737373] uppercase tracking-wider bg-[#FAFAFA]">
                      {col.name?.some || `Col_${i}`}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E5E5]">
                {currentTableData.rows.map((row, rowIndex) => (
                  <tr key={rowIndex} className="hover:bg-[#FAFAFA] transition-colors">
                    {row.map((cell, cellIndex) => {
                      const colName = currentTableData.schema.elements[cellIndex]?.name?.some || '';
                      const isStatus = colName.toLowerCase() === 'status' || colName.toLowerCase() === 'severity';
                      
                      let displayValue = cell;
                      if (Array.isArray(cell) && cell.length === 1 && typeof cell[0] === 'number') {
                         displayValue = new Date(cell[0] / 1000).toLocaleTimeString();
                      } else if (typeof cell === 'object' && cell !== null) {
                         displayValue = '{obj}';
                      }

                      return (
                        <td key={cellIndex} className="px-3 py-2 text-[11px] text-[#404040]">
                          {isStatus ? (
                            <span className={`px-1.5 py-0.5 text-[9px] font-bold rounded border uppercase tracking-wider ${getStatusColor(displayValue)}`}>
                              {String(displayValue)}
                            </span>
                          ) : (
                            <span className="font-mono">{String(displayValue)}</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          )
        ) : null}
      </div>
    </div>
  );
}
