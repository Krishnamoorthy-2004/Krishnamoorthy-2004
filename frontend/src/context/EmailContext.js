import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'react-hot-toast';

const EmailContext = createContext();

export const useEmail = () => {
  const context = useContext(EmailContext);
  if (!context) {
    throw new Error('useEmail must be used within an EmailProvider');
  }
  return context;
};

export const EmailProvider = ({ children }) => {
  const [emails, setEmails] = useState([]);
  const [drafts, setDrafts] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [emailAccounts, setEmailAccounts] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [loading, setLoading] = useState(false);
  const [currentFolder, setCurrentFolder] = useState('inbox');

  const fetchEmails = async (accountId = null) => {
    try {
      setLoading(true);
      const params = accountId ? { account_id: accountId } : {};
      const response = await axios.get('/api/emails/inbox', { params });
      setEmails(response.data.emails || []);
    } catch (error) {
      console.error('Failed to fetch emails:', error);
      toast.error('Failed to fetch emails');
    } finally {
      setLoading(false);
    }
  };

  const fetchDrafts = async () => {
    try {
      const response = await axios.get('/api/emails/drafts');
      setDrafts(response.data.drafts || []);
    } catch (error) {
      console.error('Failed to fetch drafts:', error);
      toast.error('Failed to fetch drafts');
    }
  };

  const fetchTemplates = async () => {
    try {
      const response = await axios.get('/api/templates');
      setTemplates(response.data.templates || []);
    } catch (error) {
      console.error('Failed to fetch templates:', error);
      toast.error('Failed to fetch templates');
    }
  };

  const fetchCampaigns = async () => {
    try {
      const response = await axios.get('/api/campaigns');
      setCampaigns(response.data.campaigns || []);
    } catch (error) {
      console.error('Failed to fetch campaigns:', error);
      toast.error('Failed to fetch campaigns');
    }
  };

  const fetchEmailAccounts = async () => {
    try {
      const response = await axios.get('/api/email-accounts');
      setEmailAccounts(response.data.accounts || []);
      
      // Set primary account as selected if none selected
      if (!selectedAccount && response.data.accounts.length > 0) {
        const primary = response.data.accounts.find(acc => acc.is_primary);
        setSelectedAccount(primary || response.data.accounts[0]);
      }
    } catch (error) {
      console.error('Failed to fetch email accounts:', error);
      toast.error('Failed to fetch email accounts');
    }
  };

  const sendEmail = async (emailData) => {
    try {
      const params = selectedAccount ? { account_id: selectedAccount.id } : {};
      const response = await axios.post('/api/emails/send', emailData, { params });
      toast.success('Email sent successfully!');
      
      // Refresh emails
      await fetchEmails();
      
      return { success: true, data: response.data };
    } catch (error) {
      console.error('Failed to send email:', error);
      toast.error('Failed to send email');
      return { success: false, error: error.response?.data?.detail || 'Failed to send email' };
    }
  };

  const saveDraft = async (draftData, draftId = null) => {
    try {
      const params = draftId ? { draft_id: draftId } : {};
      const response = await axios.post('/api/emails/drafts', draftData, { params });
      toast.success('Draft saved successfully!');
      
      // Refresh drafts
      await fetchDrafts();
      
      return { success: true, data: response.data };
    } catch (error) {
      console.error('Failed to save draft:', error);
      toast.error('Failed to save draft');
      return { success: false, error: error.response?.data?.detail || 'Failed to save draft' };
    }
  };

  const deleteDraft = async (draftId) => {
    try {
      await axios.delete(`/api/emails/drafts/${draftId}`);
      toast.success('Draft deleted successfully!');
      
      // Refresh drafts
      await fetchDrafts();
      
      return { success: true };
    } catch (error) {
      console.error('Failed to delete draft:', error);
      toast.error('Failed to delete draft');
      return { success: false, error: error.response?.data?.detail || 'Failed to delete draft' };
    }
  };

  const connectEmailAccount = async (provider, authCode) => {
    try {
      const response = await axios.post('/api/email-accounts/connect', {
        provider,
        auth_code: authCode
      });
      
      toast.success(`${provider.charAt(0).toUpperCase() + provider.slice(1)} account connected successfully!`);
      
      // Refresh email accounts
      await fetchEmailAccounts();
      
      return { success: true, data: response.data };
    } catch (error) {
      console.error('Failed to connect email account:', error);
      toast.error('Failed to connect email account');
      return { success: false, error: error.response?.data?.detail || 'Failed to connect email account' };
    }
  };

  const createTemplate = async (templateData) => {
    try {
      const response = await axios.post('/api/templates', templateData);
      toast.success('Template created successfully!');
      
      // Refresh templates
      await fetchTemplates();
      
      return { success: true, data: response.data };
    } catch (error) {
      console.error('Failed to create template:', error);
      toast.error('Failed to create template');
      return { success: false, error: error.response?.data?.detail || 'Failed to create template' };
    }
  };

  const createCampaign = async (campaignData) => {
    try {
      const response = await axios.post('/api/campaigns', campaignData);
      toast.success('Campaign created successfully!');
      
      // Refresh campaigns
      await fetchCampaigns();
      
      return { success: true, data: response.data };
    } catch (error) {
      console.error('Failed to create campaign:', error);
      toast.error('Failed to create campaign');
      return { success: false, error: error.response?.data?.detail || 'Failed to create campaign' };
    }
  };

  const value = {
    emails,
    drafts,
    templates,
    campaigns,
    emailAccounts,
    selectedAccount,
    loading,
    currentFolder,
    setCurrentFolder,
    setSelectedAccount,
    fetchEmails,
    fetchDrafts,
    fetchTemplates,
    fetchCampaigns,
    fetchEmailAccounts,
    sendEmail,
    saveDraft,
    deleteDraft,
    connectEmailAccount,
    createTemplate,
    createCampaign
  };

  return (
    <EmailContext.Provider value={value}>
      {children}
    </EmailContext.Provider>
  );
};