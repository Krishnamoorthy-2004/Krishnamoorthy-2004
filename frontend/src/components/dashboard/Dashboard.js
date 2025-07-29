import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useEmail } from '../../context/EmailContext';
import Sidebar from './Sidebar';
import EmailList from '../email/EmailList';
import QuickActions from './QuickActions';
import StatsOverview from './StatsOverview';
import { toast } from 'react-hot-toast';

const Dashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { 
    emails, 
    emailAccounts, 
    selectedAccount, 
    loading, 
    fetchEmails, 
    fetchEmailAccounts,
    currentFolder 
  } = useEmail();
  const [searchTerm, setSearchTerm] = useState('');
  const [showConnectAccount, setShowConnectAccount] = useState(false);

  useEffect(() => {
    if (user) {
      fetchEmailAccounts();
    }
  }, [user]);

  useEffect(() => {
    if (emailAccounts.length > 0) {
      fetchEmails(selectedAccount?.id);
    }
  }, [selectedAccount, emailAccounts]);

  const handleConnectAccount = async (provider) => {
    // Mock OAuth flow
    const mockAuthCode = `mock_auth_code_${Date.now()}`;
    const { connectEmailAccount } = useEmail();
    
    const result = await connectEmailAccount(provider, mockAuthCode);
    if (result.success) {
      setShowConnectAccount(false);
      toast.success(`${provider.charAt(0).toUpperCase() + provider.slice(1)} account connected!`);
    }
  };

  const filteredEmails = emails.filter(email => 
    email.subject.toLowerCase().includes(searchTerm.toLowerCase()) ||
    email.from.toLowerCase().includes(searchTerm.toLowerCase()) ||
    email.body.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const folderCounts = {
    inbox: emails.filter(e => e.folder === 'inbox' || !e.folder).length,
    sent: emails.filter(e => e.folder === 'sent').length,
    drafts: emails.filter(e => e.folder === 'drafts').length,
    unread: emails.filter(e => !e.is_read).length,
    important: emails.filter(e => e.is_important).length
  };

  if (emailAccounts.length === 0 && !loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 bg-blue-100 rounded-full flex items-center justify-center">
              <svg className="h-6 w-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 7.89a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 className="mt-4 text-lg font-semibold text-gray-900">Connect Your Email</h3>
            <p className="mt-2 text-sm text-gray-500">
              Connect your Gmail or Outlook account to start managing your emails
            </p>
          </div>
          
          <div className="mt-6 space-y-3">
            <button
              onClick={() => handleConnectAccount('gmail')}
              className="w-full flex items-center justify-center px-4 py-3 border border-gray-300 rounded-lg shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              <svg className="h-5 w-5 mr-2" viewBox="0 0 24 24">
                <path fill="#4285f4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34a853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#fbbc05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#ea4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Connect Gmail
            </button>
            
            <button
              onClick={() => handleConnectAccount('outlook')}
              className="w-full flex items-center justify-center px-4 py-3 border border-gray-300 rounded-lg shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              <svg className="h-5 w-5 mr-2" viewBox="0 0 24 24">
                <path fill="#0078d4" d="M23.5 12c0-6.35-5.15-11.5-11.5-11.5S.5 5.65.5 12 5.65 23.5 12 23.5 23.5 18.35 23.5 12z"/>
                <path fill="#fff" d="M12 2.5c5.24 0 9.5 4.26 9.5 9.5s-4.26 9.5-9.5 9.5S2.5 17.24 2.5 12 6.76 2.5 12 2.5z"/>
                <path fill="#0078d4" d="M17.5 8.5v7h-11v-7h11z"/>
                <path fill="#fff" d="M16.5 9.5h-9v5h9v-5z"/>
              </svg>
              Connect Outlook
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar 
        currentFolder={currentFolder}
        folderCounts={folderCounts}
        user={user}
        emailAccounts={emailAccounts}
        selectedAccount={selectedAccount}
      />
      
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="bg-white shadow-sm border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <h1 className="text-xl font-semibold text-gray-900">
                {currentFolder === 'inbox' ? 'Inbox' : 
                 currentFolder === 'sent' ? 'Sent' : 
                 currentFolder === 'drafts' ? 'Drafts' : 
                 currentFolder.charAt(0).toUpperCase() + currentFolder.slice(1)}
              </h1>
              {selectedAccount && (
                <span className="text-sm text-gray-500">
                  {selectedAccount.email}
                </span>
              )}
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search emails..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-64 pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <svg className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              
              <button
                onClick={() => navigate('/compose')}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center"
              >
                <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Compose
              </button>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <div className="flex-1 overflow-hidden">
          {currentFolder === 'inbox' && (
            <div className="p-6">
              <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-6">
                <div className="lg:col-span-3">
                  <StatsOverview />
                </div>
                <div className="lg:col-span-1">
                  <QuickActions />
                </div>
              </div>
            </div>
          )}
          
          <div className="flex-1 px-6 pb-6">
            <EmailList 
              emails={filteredEmails}
              loading={loading}
              searchTerm={searchTerm}
              folder={currentFolder}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;