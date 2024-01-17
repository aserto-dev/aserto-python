//go:build mage
// +build mage

package main

import (
	"fmt"
	"os"
	"strings"

	"github.com/aserto-dev/mage-loot/common"
	"github.com/aserto-dev/mage-loot/deps"
	"github.com/magefile/mage/sh"
)

func init() {
	os.Setenv("GO_VERSION", "1.19")
	os.Setenv("GOPRIVATE", "github.com/aserto-dev")
}

// install required dependencies.
func Deps() {
	deps.GetAllDeps()
}

func Bump(next string) error {
	nextVersion, err := common.NextVersion(next)
	if err != nil {
		return err
	}
	fmt.Println("Bumping version to", nextVersion)

	input, err := os.ReadFile("pyproject.toml")
	if err != nil {
		return err
	}

	lines := strings.Split(string(input), "\n")

	for i, line := range lines {
		if strings.Contains(line, "version = \"") {
			lines[i] = "version = \"" + nextVersion + "\""
		}
	}
	output := strings.Join(lines, "\n")

	return os.WriteFile("pyproject.toml", []byte(output), 0644)
}

func Build() error {
	err := os.RemoveAll("dist")
	if err != nil {
		return err
	}

	return sh.RunV("poetry", "build")
}

func Push() error {
	return sh.RunV("poetry", "publish")
}

func Release() error {
	err := Build()
	if err != nil {
		return err
	}

	return Push()
}
