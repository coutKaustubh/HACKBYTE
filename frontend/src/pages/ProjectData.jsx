import { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import { AlertCircle, RefreshCw, Database } from 'lucide-react';

const TABLES = ['incident', 'execution', 'ai_decision', 'safety_check', 'agent_event'];

export default function ProjectData() {
  const [activeTab, setActiveTab] = useState(TABLES[0]);
  const [data, setData] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const fetchProjectData = async () => {
    setLoading(true);
    setError(null);
    const newData = {};

    try {
      await Promise.all(TABLES.map(async (tableName) => {
        const response = await fetch('http://127.0.0.1:3000/v1/database/realitypatch-db-2lsay/sql', {
          method: 'POST',
          headers: {
            'Content-Type': 'text/plain',
          },
          body: `SELECT * FROM ${tableName}`
        });
        console.log(response);

        if (!response.ok) {
          throw new Error(`Failed to fetch ${tableName}`);
        }

        const json = await response.json();
        // The API returns an array, usually we need the first result set
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
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col">
      <Navbar showLogout={false} />

      <main className="flex-1 p-6 max-w-7xl mx-auto w-full flex flex-col">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold text-[#171717] mb-2 flex items-center gap-2">
              <Database className="w-8 h-8 text-accent" />
              Project Data Explorer
            </h1>
            <p className="text-[#737373]">
              Raw database view across runtime tables.
              {lastRefreshed && ` Last refreshed: ${lastRefreshed.toLocaleTimeString()}`}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 cursor-pointer text-sm font-medium text-[#737373] hover:text-[#171717]">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-[#E5E5E5] text-[#171717] focus:ring-[#171717]"
              />
              Auto-refresh (3s)
            </label>
            <button
              onClick={fetchProjectData}
              disabled={loading || autoRefresh}
              className="px-6 py-2.5 bg-[#171717] hover:bg-[#262626] disabled:opacity-50 text-white font-semibold rounded shadow transition-colors flex items-center justify-center gap-2"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
              Load Project Data
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <p className="text-sm font-medium">{error}</p>
          </div>
        )}

        {/* Tabs & Table Container */}
        <div className="bg-white border border-[#E5E5E5] rounded-xl shadow-sm flex flex-col flex-1 overflow-hidden">

          {/* Tabs */}
          <div className="flex overflow-x-auto border-b border-[#E5E5E5] px-2 py-2 gap-2 bg-[#FAFAFA]">
            {TABLES.map(table => (
              <button
                key={table}
                onClick={() => setActiveTab(table)}
                className={`px-4 py-2 text-sm font-semibold rounded-md transition-colors whitespace-nowrap
                  ${activeTab === table
                    ? 'bg-white text-[#171717] shadow-sm border border-[#E5E5E5]'
                    : 'text-[#737373] hover:text-[#171717] hover:bg-black/5 border border-transparent'
                  }`}
              >
                {table.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
              </button>
            ))}
          </div>

          {/* Table Area */}
          <div className="flex-1 overflow-auto bg-white p-0 relative min-h-[400px]">
            {loading && !currentTableData ? (
              <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
                <RefreshCw className="w-8 h-8 text-[#A3A3A3] animate-spin" />
              </div>
            ) : currentTableData ? (
              currentTableData.rows.length === 0 ? (
                <div className="flex items-center justify-center h-full text-[#737373] flex-col gap-2 pt-20">
                  <Database className="w-12 h-12 text-[#E5E5E5]" />
                  <p>No records found in <strong>{activeTab}</strong>.</p>
                </div>
              ) : (
                <table className="w-full text-left border-collapse min-w-max">
                  <thead className="bg-[#FAFAFA] border-b border-[#E5E5E5] sticky top-0 z-10">
                    <tr>
                      {currentTableData.schema.elements.map((col, i) => {
                        const colName = col.name?.some || `Column_${i}`;
                        return (
                          <th key={i} className="px-5 py-3 text-xs font-semibold text-[#737373] uppercase tracking-wider">
                            {colName}
                          </th>
                        );
                      })}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E5E5E5]">
                    {currentTableData.rows.map((row, rowIndex) => (
                      <tr key={rowIndex} className="hover:bg-[#FAFAFA] transition-colors">
                        {row.map((cell, cellIndex) => {
                          const colName = currentTableData.schema.elements[cellIndex]?.name?.some || '';
                          const isStatus = colName.toLowerCase() === 'status' || colName.toLowerCase() === 'severity';

                          // Handle complex structures like timestamp arrays
                          let displayValue = cell;
                          if (Array.isArray(cell) && cell.length === 1 && typeof cell[0] === 'number') {
                            displayValue = new Date(cell[0] / 1000).toLocaleString();
                          } else if (typeof cell === 'object' && cell !== null) {
                            displayValue = JSON.stringify(cell);
                          }

                          return (
                            <td key={cellIndex} className="px-5 py-4 text-sm text-[#404040]">
                              {isStatus ? (
                                <span className={`px-2.5 py-1 text-xs font-semibold rounded border uppercase tracking-wider ${getStatusColor(displayValue)}`}>
                                  {String(displayValue)}
                                </span>
                              ) : (
                                <span className="font-mono text-[13px]">{String(displayValue)}</span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-[#A3A3A3] pt-20">
                <Database className="w-16 h-16 mb-4 text-[#F5F5F5]" />
                <p className="text-lg font-medium text-[#737373]">Click "Load Project Data" to begin.</p>
                <p className="text-sm">This will fetch the latest rows from all tables.</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
