function lcstool_dg_benchmark(run_config_json)
% Benchmark script for double gyre example
%   run_config_json: json file containing the following keys
%   keys listed below
    %   flow_data: struct containing flow_data
    %   output_json_path: full path to save JSON results
    %   iterates_per_run: number of iterates to perfrom
    %   num_benchmark_runs: how many times to run the benchmark
    %   error_data: (optional) struct storing path to error data and params

    disp('--- MATLAB Benchmark: double_gyre_ftle ---');
    json_config = jsondecode(fileread(run_config_json));
    flow_data = json_config.flow_data;
    t0 = flow_data.t0;
    T = flow_data.T;
    dt0 = flow_data.dt0;
    output_json_path = json_config.output_json_path;
    iterates_per_run = json_config.iterates_per_run;
    num_benchmark_runs = json_config.num_benchmark_runs;
    error_data = json_config.error_data;
    disp(['Output JSON: ', output_json_path]);
    disp(['Benchmark Iterations: ', num2str(num_benchmark_runs)]);
    
    script_dir = fileparts(mfilename('fullpath')); % script dir
    addpath(fullfile(script_dir, 'matlab_rhs'), '-begin'); %add rhs path

    lcstool_path = getenv("LCSTOOL_PATH"); % get lcstool path

    if isempty(lcstool_path)
        error('CRITICAL: Environment variable LCSTOOL_PATH is not set.');
    end
    if ~isfolder(lcstool_path)
        error('CRITICAL: LCSTOOL_PATH is not a valid folder: %s', lcstool_path);
    end
    addpath(genpath(lcstool_path), '-begin'); % genpath adds all subfolders
    disp(['Added LCStool code path: ', lcstool_path]);
    disp(['Added local script path: ', script_dir]);

    
    % Input parameters
    epsilon = .25;
    amplitude = .1;
    omega = pi/5;
    timespan = [t0,T];
    domain = [0,2;0,1];
    resolutionX = 201;
    [resolutionY,~] = equal_resolution(domain,resolutionX);
    resolution = [resolutionX,resolutionY];
    % Velocity definition
    lDerivative = @(t,x,~)dg_derivative(t,x,false,epsilon,amplitude,omega);
    incompressible = true;
    
    % Initialize results struct
    results = struct();
    
    % Cauchy-Green strain
    cgStrainOdeSolverOptions = odeset('relTol',1e-6,'AbsTol',1e-8);
    disp('Starting warm-up...')
    if ~isempty(fieldnames(error_data))
        if ~isstruct(error_data)
            error('error_data was passed but it must be a struct')
        else
            ftle_true = transpose(double(py.numpy.load(error_data.path)));
            t0_true = error_data.t0;
            tic;
            % Cauchy-Green strain eigenvalues and eigenvectors
            [~,cgEigenvalue] = eig_cgStrain( ...
                lDerivative, ...
                domain, ...
                resolution, ...
                [t0_true, t0_true + T], ...
                'incompressible',incompressible, ...
                'odeSolverOptions',cgStrainOdeSolverOptions ...
                );
            
            % Compute finite-time Lyapunov exponent
            cgEigenvalue2 = reshape(cgEigenvalue(:,2),fliplr(resolution));
            ftle_ = ftle(cgEigenvalue2,diff(timespan));
            warmup_time = toc;

            ftle_true = ftle_true(2:end-1, 2:end-1);
            ftle_ = ftle_(2:end-1, 2:end-1);

            n = numel(ftle_) - numnan(ftle_);
            mae_ = sum(abs(ftle_true - ftle_), 'all')/n;
            results.error = struct( ...
                'mae', mae_, 'error_params', error_data.error_params ...
                );      
        end
    else
        tic;
        % Cauchy-Green strain eigenvalues and eigenvectors
        [~,cgEigenvalue] = eig_cgStrain( ...
            lDerivative, ...
            domain, ...
            resolution, ...
            timespan, ...
            'incompressible',incompressible, ...
            'odeSolverOptions',cgStrainOdeSolverOptions ...
            );
        
        % Compute finite-time Lyapunov exponent
        cgEigenvalue2 = reshape(cgEigenvalue(:,2),fliplr(resolution));
        ftle_ = ftle(cgEigenvalue2,diff(timespan));
        warmup_time = toc;
    end
    disp("Warm-up complete.")
    if num_benchmark_runs == 1
        tic;
        for k = 1:iterates_per_run
            % Cauchy-Green strain eigenvalues and eigenvectors
            [~,cgEigenvalue] = eig_cgStrain( ...
                lDerivative, ...
                domain, ...
                resolution, ...
                timespan + (k-1)*dt0, ...
                'incompressible',incompressible, ...
                'odeSolverOptions',cgStrainOdeSolverOptions ...
                );
            
            % Plot finite-time Lyapunov exponent
            cgEigenvalue2 = reshape(cgEigenvalue(:,2),fliplr(resolution));
            ftle_ = ftle(cgEigenvalue2,diff(timespan));
        end
        % Compute timings
        loop_time = toc;
        per_iter_time = loop_time/iterates_per_run;
        % Store timings
        results.benchmark_script = mfilename;
        results.parameters = struct( ...
            'iterates_per_run', iterates_per_run, ...
            'num_benchmark_runs', num_benchmark_runs ...
            );
        results.timings = struct( ...
            'warmup_time', warmup_time, ...
            'mean_loop_time', loop_time, ...
            'mean_per_iter_time', per_iter_time, ...
            'std_loop_times', 0, ...
            'std_per_iter_time', 0 ...
        );
    elseif num_benchmark_runs < 1
        error('num_benchmark_runs must be at least 1');
    else
        loop_times = zeros(1, num_benchmark_runs);
        for i = 1:num_benchmark_runs
            tic;
            for k = 1:iterates_per_run
                % Cauchy-Green strain eigenvalues and eigenvectors
                [~,cgEigenvalue] = eig_cgStrain( ...
                    lDerivative, ...
                    domain, ...
                    resolution, ...
                    timespan + (k-1)*dt0, ...
                    'incompressible',incompressible, ...
                    'odeSolverOptions',cgStrainOdeSolverOptions ...
                    );
                
                % Plot finite-time Lyapunov exponent
                cgEigenvalue2 = reshape(cgEigenvalue(:,2),fliplr(resolution));
                ftle_ = ftle(cgEigenvalue2,diff(timespan));
            end
            % Compute timings
            loop_time = toc;
            loop_times(i) = loop_time;
        end
        per_iter_times = loop_times/iterates_per_run;
        % Store timings
        results.benchmark_script = mfilename;
        results.parameters = struct( ...
            'iterates_per_run', iterates_per_run, ...
            'num_benchmark_runs', num_benchmark_runs ...
            );
        results.timings = struct( ...
            'warmup_time', warmup_time, ...
            'loop_times', loop_times, ...
            'per_iter_times', per_iter_times, ...
            'mean_loop_time', mean(loop_times), ...
            'mean_per_iter_time', mean(per_iter_times), ...
            'std_loop_times', std(loop_times), ...
            'std_per_iter_time', std(per_iter_times) ...
            );
    end
    results.metadata = json_config.metadata;
    disp(['Saving results to: ', output_json_path]);
    try
        json_str = jsonencode(results, 'PrettyPrint', true);
        fid = fopen(output_json_path, 'w');
        if fid == -1
            error('Cannot open output file: %s', output_json_path)
        end
        fprintf(fid, '%s', json_str);
        fclose(fid);
    catch ME
        fprintf(2, 'Error saving JSON: %s\n', ME.message);
        rethrow(ME);
    end
    disp('LCStool benchmark complete.');
end

