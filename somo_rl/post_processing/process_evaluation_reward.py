import os
import pdb
import sys
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, path)

from somo_rl.user_settings import EXPERIMENT_ABS_PATH
import pickle

# print("PATH", EXPERIMENT_ABS_PATH )
class Process_reward_data:
    def __init__(self, exp_abs_path, run_ID):
        self.run_ID = run_ID
        self.run_dir = Path(exp_abs_path)
        for subdivision in self.run_ID:
            self.run_dir = self.run_dir / subdivision
        self.evaluation_dir = self.run_dir / "results_rollout/rollout_data"
        self.reward_plots_dir = self.run_dir / "results_rollout" / "reward_plots"
        os.makedirs(self.reward_plots_dir, exist_ok=True)
        self.processed_rollout_dir = self.run_dir / "results_rollout/rollout_data_processed"
        os.makedirs(self.processed_rollout_dir, exist_ok=True)
        self.evaluation_means_path = self.processed_rollout_dir / "evaluation_means_.pkl"
        self.evaluation_stds_path = self.processed_rollout_dir / "evaluation_stds_.pkl"
        # self.evaluation_log_dfs_len = None

    def process_evaluation_data(self):
        # Calculating std of the `monitor` files

        evaluation_subdir = [x[0] for x in os.walk(self.evaluation_dir)][1:]

        evaluation_log_dfs = [None] * len(evaluation_subdir)
        # self.evaluation_log_dfs_len = len(evaluation_log_dfs)
        for i, evaluation_subdir_ in enumerate(evaluation_subdir):
            evaluation_log_dfs[i] = pickle.load(open(Path(evaluation_subdir_) / 'reward_components.pkl', 'rb'))

        evaluation_df_concat = pd.concat(evaluation_log_dfs)
        by_row_index = evaluation_df_concat.groupby(evaluation_df_concat.index)
        self.evaluation_means_df = by_row_index.mean()
        self.evaluation_stds_df = by_row_index.std(ddof=0)  # population standard deviation

        self.evaluation_means_df.to_pickle(self.evaluation_means_path)
        self.evaluation_stds_df.to_pickle(self.evaluation_stds_path)

    def get_moving_avg(self, data, window_size):
        moving_avg = np.convolve(data, np.ones(window_size), 'valid') / window_size
        return moving_avg

    # def get_x_data(self, x_units="steps", max_x_val=None):
    #     if x_units == "hours":
    #         times = self.evaluation_means_df["t"]
    #         x = np.array(times) / (60 * 60)
    #     elif x_units == "episodes":
    #         x = np.array(range(len(self.evaluation_means_df)))
    #     elif x_units == "steps":
    #         mean_lengths = self.evaluation_means_df["l"]
    #         x = np.array([0] * len(mean_lengths))
    #         x[0] = mean_lengths[0]
    #         for i in range(1, len(mean_lengths)):
    #             x[i] = x[i - 1] + mean_lengths[i]
    #     data_len = len(x)
    #     if max_x_val is not None and x[-1] > max_x_val:
    #         data_len = np.argmax(x > max_x_val)
    #     return x[:data_len]

    def plot(
            self, ax, title="", ylabel="", label="", log_component="step_reward", x_units="steps", max_x_val=None, smoothed=False,
            ref_line_data=None, ref_line_name="No Action Taken"
    ):
        window_size = 10
        avg_data = self.evaluation_means_df['step_reward']
        std_data = self.evaluation_stds_df['step_reward']

        x = np.arange(len(self.evaluation_means_df.index))
        y = avg_data
        std = std_data

        moving_avg = self.get_moving_avg(y, window_size)
        moving_avg_xs = self.get_moving_avg(x, window_size)

        ax.set_title(title, fontsize=10)
        ax.set_ylabel(ylabel)
        ax.set_xlabel(x_units)
        label = log_component if label == "" else label
        if not smoothed:
            p = ax.plot(x, y, label=label)[0]
            ax.fill_between(x, y - std, y + std, color=p.get_color(), alpha=0.1)
        else:
            ax.set_title(f"smoothed {title}", fontsize=10)
            ax.plot(moving_avg_xs, moving_avg, label=f"smoothed {label}")

        if ref_line_data is not None:
            ax.plot(x, [ref_line_data] * len(x), "k--", label=ref_line_name)

        ax.grid()


def process_reward_data(
        exp_abs_path,
        exp_name,
        run_group_name,
        run_name,
        log_components=("step_reward"),
        x_units="steps",
        max_x_val=None,
        smoothed=False,
        show=True,
        save_figs=True
):
    run_ID = [exp_name, run_group_name, run_name]
    reward_data = Process_reward_data(exp_abs_path=exp_abs_path, run_ID=run_ID)
    reward_data.process_evaluation_data()

    max_num_cols = 3
    num_rows = int(np.ceil(len(log_components) / max_num_cols))
    num_cols = int(min(len(log_components), max_num_cols))

    fig, ax = plt.subplots(num_rows, num_cols)

    evaluation_dir_ = Path(EXPERIMENT_ABS_PATH) / exp_name / run_group_name / run_name / "results_rollout/rollout_data"
    evaluation_subdir_ = [x[0] for x in os.walk(evaluation_dir_)][1:]

    plt.suptitle(f"Reward during policy rollout in one episode of 1k steps over {len(evaluation_subdir_)} runs", fontsize=10)

    if num_rows > 1 or num_cols > 1:
        ax = ax.ravel()
    else:
        ax = [ax]

    for i, log_component in enumerate(log_components):
        ref_line_data = None
        ref_line_name = None

        reward_data.plot(
            ax[i],
            title=log_component,
            ylabel=f"{log_component} value",
            log_component=log_component,
            x_units=x_units,
            max_x_val=max_x_val,
            smoothed=smoothed,
            ref_line_data=ref_line_data,
            ref_line_name=ref_line_name
        )

    plt.tight_layout()

    if save_figs:
        plt.savefig(reward_data.reward_plots_dir / (f"rewards_plot_{len(evaluation_subdir_)}runs.png"))
        plt.savefig(reward_data.reward_plots_dir / (f"rewards_plot_{len(evaluation_subdir_)}runs.eps"), format="eps")

    if show:
        plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="postprocess run argument parser")
    parser.add_argument(
        "-e",
        "--exp_name",
        help="Experiment name",
        required=True,
        default=None,
    )
    parser.add_argument(
        "--exp_abs_path",
        help="Experiment directory absolute path",
        required=False,
        default=EXPERIMENT_ABS_PATH,
    )
    parser.add_argument(
        "-g",
        "--run_group_name",
        help="Run-group name",
        required=True,
        default=None,
    )
    parser.add_argument(
        "-r",
        "--run_name",
        help="Run Name",
        required=True,
        default=None,
    )
    parser.add_argument('-lc', '--log_components', nargs='+',
                        help='List of logged components to plot (space separated).', required=False, default=["step_reward"])
    parser.add_argument(
        "--smoothed",
        help="smooth data",
        action="store_true",
    )
    parser.add_argument(
        "--save",
        help="save plots",
        action="store_true",
    )

    arg = parser.parse_args()

    process_reward_data(
        arg.exp_abs_path,
        arg.exp_name,
        arg.run_group_name,
        arg.run_name,
        log_components=arg.log_components,
        x_units="steps",
        max_x_val=None,
        smoothed=arg.smoothed,
        show=True,
        save_figs=arg.save
    )