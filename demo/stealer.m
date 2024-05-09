% 這是用來把把資料從EDF幹出來，再仿造SSVEP-Analysis-TOOL的模型建構data(‘第幾個Channel個數’, ‘第幾個時間點’, ‘第幾個頻率’, and ‘第幾組實驗’)
% 建構出 4-D data (13, 10000, 8, 5)


% EEGLAB history file generated on the 04-Apr-2024
% ------------------------------------------------

% Read data
% [ALLEEG EEG CURRENTSET ALLCOM] = eeglab;
% EEG = pop_biosig('C:\Users\USER\ArtiseBio\0327_8-15hz_20sec_trail1.edf'); 
% [ALLEEG EEG CURRENTSET] = pop_newset(ALLEEG, EEG, 0,'gui','off');
% 
% % Filter 1~200
% EEG = pop_eegfiltnew(EEG, 'locutoff',1,'hicutoff',200,'plotfreqz',1);
% [ALLEEG EEG CURRENTSET] = pop_newset(ALLEEG, EEG, 1,'setname','filter 1~200','gui','off'); 
% 
% % Notch ilter 40~60
% EEG = pop_eegfiltnew(EEG, 'locutoff',40,'hicutoff',60,'revfilt',1,'plotfreqz',1);
% [ALLEEG EEG CURRENTSET] = pop_newset(ALLEEG, EEG, 2,'setname','notch 40~60','gui','off'); 
% 
% % Select right channel
% EEG = pop_select( EEG, 'channel',{'TP7','CP3','CPz','CP4','TP8','P7','P3','Pz','P4','P8','O1','Oz','O2'});
% [ALLEEG EEG CURRENTSET] = pop_newset(ALLEEG, EEG, 3,'setname','select channel','gui','off'); 

% !Extract epoch, get a data w/ 10001 frames
% EEG = pop_rmdat( EEG, {'10, Expr 20s'},[0 20] ,0);

data = ones(31, 10000, 8, 5)

for block = 1:5
    [ALLEEG EEG CURRENTSET ALLCOM] = eeglab;
    block_str = sprintf('C:\\Users\\USER\\ArtiseBio\\0327_8-15hz_20sec_trail%d.edf', block);
    EEG = pop_biosig(block_str);
    % Filter 1~200
    EEG = pop_eegfiltnew(EEG, 'locutoff',1,'hicutoff',200,'plotfreqz',1);
    % Notch ilter 40~60
    EEG = pop_eegfiltnew(EEG, 'locutoff',40,'hicutoff',60,'revfilt',1,'plotfreqz',1);

    % Rereference to 'CPz'
    EEG = pop_reref( EEG, 22);

    % % Select right channel
    % EEG = pop_select( EEG, 'channel',{'TP7','CP3','CPz','CP4','TP8','P7','P3','Pz','P4','P8','O1','Oz','O2'});

    setname = sprintf('Block %d - Processed', block);
    [ALLEEG, EEG, baseCURRENTSET] = pop_newset(ALLEEG, EEG, CURRENTSET, 'setname', setname, 'gui', 'off');

    for freq_idx = 1:8
        % 在每次循环开始时，从基础数据集开始
        EEG = ALLEEG(baseCURRENTSET); % 返回到基础数据集
        CURRENTSET = baseCURRENTSET;

        % 根据freq_idx切分不同的epoch
        str_tmp = sprintf('%d, Expr 20s', freq_idx+7);  % start from 8~15
        tmp_eeg = pop_rmdat( EEG, {str_tmp},[0 20], 0);

        % 处理epoch数据，并保存结果
        for chan = 1:31
            data(chan, :, freq_idx, block) = tmp_eeg.data(chan, 1:10000);
        end
    end
end
