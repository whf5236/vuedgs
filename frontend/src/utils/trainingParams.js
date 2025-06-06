// 训练参数管理模块
export class TrainingParams {
  // 默认训练参数
  static getDefaultParams() {
    return {
      iterations: 30000,
      position_lr_init: 0.00016,
      position_lr_final: 0.0000016,
      position_lr_delay_mult: 0.01,
      position_lr_max_steps: 30000,
      feature_lr: 0.0025,
      opacity_lr: 0.05,
      scaling_lr: 0.005,
      rotation_lr: 0.001,
      percent_dense: 0.01,
      lambda_dssim: 0.2,
      densification_interval: 100,
      opacity_reset_interval: 3000,
      densify_from_iter: 500,
      densify_until_iter: 15000,
      densify_grad_threshold: 0.0002,
      random_background: false,
      white_background: false,
      resolution: -1,
      data_device: 'cuda',
      eval: false,
      convert_SHs_python: false,
      compute_cov3D_python: false,
      debug: false,
      debug_from: -1,
      detect_anomaly: false,
      test_iterations: [7000, 30000],
      save_iterations: [7000, 30000],
      quiet: false,
      checkpoint_iterations: [],
      start_checkpoint: null
    };
  }

  // 验证参数
  static validateParams(params) {
    const errors = [];

    // 验证迭代次数
    if (!params.iterations || params.iterations <= 0) {
      errors.push('迭代次数必须大于0');
    }

    // 验证学习率
    if (params.position_lr_init <= 0) {
      errors.push('初始位置学习率必须大于0');
    }

    if (params.feature_lr <= 0) {
      errors.push('特征学习率必须大于0');
    }

    // 验证密集化参数
    if (params.densify_from_iter >= params.densify_until_iter) {
      errors.push('密集化开始迭代必须小于结束迭代');
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }

  // 格式化参数用于API调用
  static formatParamsForAPI(params) {
    const cleanedParams = { ...params };
    
    // 确保迭代次数是整数
    cleanedParams.iterations = parseInt(cleanedParams.iterations, 10);
    cleanedParams.position_lr_max_steps = parseInt(cleanedParams.position_lr_max_steps, 10);
    cleanedParams.densification_interval = parseInt(cleanedParams.densification_interval, 10);
    cleanedParams.opacity_reset_interval = parseInt(cleanedParams.opacity_reset_interval, 10);
    cleanedParams.densify_from_iter = parseInt(cleanedParams.densify_from_iter, 10);
    cleanedParams.densify_until_iter = parseInt(cleanedParams.densify_until_iter, 10);
    cleanedParams.debug_from = parseInt(cleanedParams.debug_from, 10);
    cleanedParams.resolution = parseInt(cleanedParams.resolution, 10);

    // 确保学习率等是浮点数
    cleanedParams.position_lr_init = parseFloat(cleanedParams.position_lr_init);
    cleanedParams.position_lr_final = parseFloat(cleanedParams.position_lr_final);
    cleanedParams.position_lr_delay_mult = parseFloat(cleanedParams.position_lr_delay_mult);
    cleanedParams.feature_lr = parseFloat(cleanedParams.feature_lr);
    cleanedParams.opacity_lr = parseFloat(cleanedParams.opacity_lr);
    cleanedParams.scaling_lr = parseFloat(cleanedParams.scaling_lr);
    cleanedParams.rotation_lr = parseFloat(cleanedParams.rotation_lr);
    cleanedParams.percent_dense = parseFloat(cleanedParams.percent_dense);
    cleanedParams.lambda_dssim = parseFloat(cleanedParams.lambda_dssim);
    cleanedParams.densify_grad_threshold = parseFloat(cleanedParams.densify_grad_threshold);

    // 解析由空格分隔的字符串
    if (typeof cleanedParams.test_iterations === 'string') {
      cleanedParams.test_iterations = this.parseIterations(cleanedParams.test_iterations);
    }
    if (typeof cleanedParams.save_iterations === 'string') {
      cleanedParams.save_iterations = this.parseIterations(cleanedParams.save_iterations);
    }
    if (typeof cleanedParams.checkpoint_iterations === 'string') {
      cleanedParams.checkpoint_iterations = this.parseIterations(cleanedParams.checkpoint_iterations);
    }

    // 移除不应发送到后端的字段
    delete cleanedParams.source_path; // source_path 将由调用者单独处理

    return cleanedParams;
  }

  // 解析迭代字符串
  static parseIterations(iterString) {
    if (typeof iterString !== 'string' || !iterString) return [];
    
    try {
      // 支持逗号或空格分隔
      return iterString.split(/[\s,]+/).map(iter => parseInt(iter.trim())).filter(iter => !isNaN(iter));
    } catch (error) {
      console.error('解析迭代字符串失败:', error);
      return [];
    }
  }

  // 重置参数到默认值
  static resetToDefaults() {
    return this.getDefaultParams();
  }
}